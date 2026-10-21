import os

import sys

import json

import asyncio

from urllib.parse import quote_plus

from pathlib import Path

from playwright.async_api import async_playwright

from mcp.server.fastmcp import FastMCP

# Asegurar resolución de módulos locales de MCP Linkedin

CURRENT_DIR = Path(__file__).parent.resolve()

if str(CURRENT_DIR) not in sys.path:

    sys.path.insert(0, str(CURRENT_DIR))

from linkedin_interactive_login import (
    trigger_interactive_session_renewal,
    sync_cookies_from_brave_cdp,
    sanitize_cookies,
    save_storage_state_atomically,
    CREDS_FILE,
    STORAGE_STATE_FILE,
    AUTH_DIR,
    get_brave_path
)
import linkedin_extended as le
import linkedin_intelligence as li

mcp = FastMCP("linkedin")

USER_PROFILE = os.environ.get("USERPROFILE", os.path.expanduser("~"))

# Detección inteligente del navegador Brave o Chromium
BRAVE_PATH = get_brave_path()

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def get_creds() -> dict:
    # 1. Variables de entorno directas
    env_email = os.environ.get("LINKEDIN_EMAIL")
    env_pass = os.environ.get("LINKEDIN_PASSWORD")
    if env_email and env_pass:
        return {"email": env_email, "password": env_pass}

    # 2. Archivo de credenciales JSON
    if not CREDS_FILE.exists():
        if STORAGE_STATE_FILE.exists():
            return {}
        raise FileNotFoundError(
            f"LinkedIn credentials not found. Configure LINKEDIN_EMAIL/LINKEDIN_PASSWORD in .env or provide {CREDS_FILE}"
        )

    with open(CREDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

async def get_my_profile_url(page) -> str:
    """Detecta dinámicamente la URL del perfil del usuario autenticado."""
    try:
        url = await page.evaluate(r'''() => {
            const a = document.querySelector('a.global-nav__primary-link[href*="/in/"]') ||
                      document.querySelector('.feed-identity-module a[href*="/in/"]') ||
                      document.querySelector('a[href*="/in/"]');
            return a ? a.href.split('?')[0].replace(/\/$/, '') : '';
        }''')
        if url and "/in/" in url:
            return url
    except Exception:
        pass
    return "https://www.linkedin.com/feed"

async def get_my_activity_url(page) -> str:
    """Resuelve dinámicamente la URL de actividad reciente del usuario autenticado."""
    profile_url = await get_my_profile_url(page)
    if "/in/" in profile_url:
        return f"{profile_url}/recent-activity/all/"
    return "https://www.linkedin.com/feed/"

class ContextWrapper:

    def __init__(self, context, is_cdp: bool):

        self._context = context

        self.is_cdp = is_cdp

        self._pages = []

    def __getattr__(self, name):

        return getattr(self._context, name)

    async def new_page(self):

        page = await self._context.new_page()

        self._pages.append(page)

        return page

    async def close_pages(self):

        for p in self._pages:

            try:

                await p.close()

            except Exception:

                pass

        self._pages.clear()

class BrowserWrapper:

    def __init__(self, browser, context_wrapper, is_cdp: bool):

        self._browser = browser

        self._context_wrapper = context_wrapper

        self.is_cdp = is_cdp

    def __getattr__(self, name):

        return getattr(self._browser, name)

    async def close(self):

        if self._context_wrapper:

            await self._context_wrapper.close_pages()

        if not self.is_cdp:

            try:

                await self._browser.close()

            except Exception:

                pass

async def get_browser_and_context(playwright, headless: bool = True):

    """

    Instancia el motor nativo de Brave Browser con evasión de fingerprints

    y carga persistente de cookies de sesión auténticas (storage_state.json).

    """

    launch_kwargs = {

        "headless": headless,

        "args": [

            "--no-sandbox",

            "--disable-blink-features=AutomationControlled"

        ]

    }

    if os.path.exists(BRAVE_PATH):

        launch_kwargs["executable_path"] = BRAVE_PATH

    browser = await playwright.chromium.launch(**launch_kwargs)

    context_kwargs = {

        "user_agent": USER_AGENT,

        "viewport": {"width": 1280, "height": 950},

        "locale": "es-ES"

    }

    # Paso 0: Sincronización silenciosa y atómica desde Brave CDP (puerto 9222) si está disponible
    sync_cookies_from_brave_cdp()

    loaded_state = None

    if STORAGE_STATE_FILE.exists():

        try:

            with open(STORAGE_STATE_FILE, "r", encoding="utf-8") as f:

                raw_st = json.load(f)

            if "cookies" in raw_st and isinstance(raw_st["cookies"], list):

                raw_st["cookies"] = sanitize_cookies(raw_st["cookies"])

                with open(STORAGE_STATE_FILE, "w", encoding="utf-8") as fw:

                    json.dump(raw_st, fw, indent=2)

                loaded_state = raw_st

        except Exception as e:

            print(f"[MCP Linkedin] Error procesando storage_state previo: {e}")

    try:

        if loaded_state:

            context = await browser.new_context(storage_state=loaded_state, **context_kwargs)

        else:

            context = await browser.new_context(**context_kwargs)

    except Exception as ctx_err:

        print(f"[MCP Linkedin] Error instanciando contexto con storage_state: {ctx_err}. Reintentando contexto limpio...")

        context = await browser.new_context(**context_kwargs)

    return browser, context

async def ensure_authenticated(page, creds: dict):

    """
    Valida la vigencia de la sesión activa en el feed de LinkedIn.
    Prioriza SIEMPRE la sesión activa en Brave Browser (CDP 9222) de forma silenciosa.
    Solo recurre al login desatendido o al Plan B en caso de fallo absoluto.
    """

    # 1. Comprobación rápida de URL previa
    if ("feed" in page.url or "/in/" in page.url) and "login" not in page.url and "checkpoint" not in page.url and "uas" not in page.url:
        return page

    # 2. Navegar al feed con los cookies existentes para verificar sesión
    try:
        await page.goto("https://www.linkedin.com/feed/", wait_until="commit", timeout=12000)
        await page.wait_for_timeout(2500)
    except Exception:
        pass

    if ("feed" in page.url or "/in/" in page.url) and "login" not in page.url and "checkpoint" not in page.url and "uas" not in page.url:
        return page

    # 3. Sincronización en caliente desde Brave CDP si la navegación previa no entró al feed
    if sync_cookies_from_brave_cdp():
        try:
            with open(STORAGE_STATE_FILE, "r", encoding="utf-8") as f:
                raw_st = json.load(f)
            if "cookies" in raw_st and raw_st["cookies"]:
                await page.context.add_cookies(raw_st["cookies"])
                await page.goto("https://www.linkedin.com/feed/", wait_until="commit", timeout=12000)
                await page.wait_for_timeout(2500)
                if ("feed" in page.url or "/in/" in page.url) and "login" not in page.url and "checkpoint" not in page.url and "uas" not in page.url:
                    return page
        except Exception:
            pass

    # 4. Prohibición estricta de login automatizado por formulario (Regla Anti-Captcha).
    # Si la sesión activa no es válida, intentar restaurar desde respaldo .bak antes de pedir intervención.
    backup_file = STORAGE_STATE_FILE.with_suffix(".json.bak")
    if backup_file.exists():
        try:
            with open(backup_file, "r", encoding="utf-8") as f_bak:
                bak_st = json.load(f_bak)
            if "cookies" in bak_st and bak_st["cookies"]:
                await page.context.clear_cookies()
                await page.context.add_cookies(bak_st["cookies"])
                await page.goto("https://www.linkedin.com/feed/", wait_until="commit", timeout=12000)
                await page.wait_for_timeout(2500)
                if ("feed" in page.url or "/in/" in page.url) and "login" not in page.url and "checkpoint" not in page.url and "uas" not in page.url:
                    save_storage_state_atomically(bak_st["cookies"])
                    return page
        except Exception:
            pass

    needs_interactive = True

    # 4. PLAN B: Si no se alcanzó el feed (captcha, 2FA, checkpoint o credenciales caducadas),

    # desplegar ventana interactiva física de Brave Browser en el escritorio del usuario (/IT).

    if needs_interactive:
        print("[MCP Linkedin] Sesión no detectada. Invocando renovación interactiva en pantalla...")
        renewed = trigger_interactive_session_renewal(timeout_sec=180)
        if renewed and STORAGE_STATE_FILE.exists():
            with open(STORAGE_STATE_FILE, "r", encoding="utf-8") as f:
                new_st = json.load(f)
            if "cookies" in new_st and new_st["cookies"]:
                await page.context.clear_cookies()
                await page.context.add_cookies(new_st["cookies"])
                await page.goto("https://www.linkedin.com/feed/", wait_until="commit", timeout=12000)
                await page.wait_for_timeout(2500)
                if ("feed" in page.url or "/in/" in page.url) and "login" not in page.url and "checkpoint" not in page.url and "uas" not in page.url:
                    return page
        raise PermissionError(
            f"No se pudo completar el inicio de sesión interactivo o tiempo de espera agotado (URL actual: {page.url}). "
            "Por favor, completa el login en la ventana interactiva para continuar."
        )

    return page

async def open_post_menu(page, post_url: str = None, post_index: int = 0):

    """Navega a la publicación o actividad reciente y abre el menú de 3 puntitos."""

    if post_url:

        await page.goto(post_url, wait_until="commit")

        await page.wait_for_timeout(3500)

        btn = page.locator('button[aria-label*="menú de controles"], button[aria-label*="controles"], button[aria-label*="control"], button[aria-label*="opciones"], button.feed-shared-control-menu__trigger').first

        if await btn.count() == 0:

            raise RuntimeError(f"No se localizó el botón de controles en: {post_url}")

        await btn.click()

        await page.wait_for_timeout(1500)

    else:

        # Navegar a la actividad reciente del usuario dinámicamente
        act_url = await get_my_activity_url(page)
        await page.goto(act_url, wait_until="commit")
        await page.wait_for_timeout(3500)

        btns = page.locator('button[aria-label*="menú de controles"], button[aria-label*="controles"], button[aria-label*="control"], button[aria-label*="opciones"], button.feed-shared-control-menu__trigger, button[aria-label*="More options"]')
        total = await btns.count()
        if total <= post_index:
            raise IndexError(f"Índice de post {post_index} fuera de rango (detectados {total} posts)")

        await btns.nth(post_index).click()

        await page.wait_for_timeout(1500)

# ==========================================

# PUBLICACIONES & ACCIONES DE LOS 3 PUNTITOS

# ==========================================

@mcp.tool()
async def linkedin_create_post(
    text: str,
    image_path: str = None,
    first_comment: str = None,
    clean_previous_tests: bool = False
) -> dict:
    """
    Crea una publicación en LinkedIn con soporte opcional de imagen en alta resolución,
    primer comentario automático (para enlaces salientes) y limpieza pre-flight opcional
    de publicaciones previas de prueba (clean_previous_tests=True).
    """
    creds = get_creds()
    async with async_playwright() as p:
        browser, context = await get_browser_and_context(p)
        page = await context.new_page()
        try:
            await ensure_authenticated(page, creds)

            # Limpieza preventiva pre-flight de publicaciones de prueba previas si se solicita
            if clean_previous_tests:
                try:
                    act_url = await get_my_activity_url(page)
                    await page.goto(act_url, wait_until="commit")
                    await page.wait_for_timeout(3000)
                    menu_btn = page.locator('button[aria-label*="menú de controles"], button[aria-label*="controles"], button.feed-shared-control-menu__trigger').first
                    if await menu_btn.count() > 0:
                        await menu_btn.click()
                        await page.wait_for_timeout(1000)
                        del_item = page.locator('[role="menuitem"]:has-text("Eliminar publicación"), [role="menuitem"]:has-text("Delete post")').first
                        if await del_item.count() > 0:
                            await del_item.click()
                            await page.wait_for_timeout(1500)
                            confirm_btn = page.locator('button:has-text("Eliminar"), button:has-text("Delete")').first
                            if await confirm_btn.count() > 0:
                                await confirm_btn.click()
                                await page.wait_for_timeout(3000)
                except Exception as clean_err:
                    print(f"[MCP Linkedin] Advertencia en limpieza preventiva: {clean_err}")
                await page.goto("https://www.linkedin.com/feed/", wait_until="commit")
                await page.wait_for_timeout(2500)

            # Abrir modal de publicación
            create_btn = page.locator('div[role="button"]:has-text("Crear publicación"), div[aria-label="Crear publicación"], button:has-text("Crear publicación")').first
            await create_btn.click()
            await page.wait_for_timeout(2000)

            # Adjuntar imagen si se solicita

            if image_path:

                abs_img = os.path.abspath(image_path)

                if not os.path.exists(abs_img):

                    raise FileNotFoundError(f"Imagen no encontrada: {abs_img}")

                async with page.expect_file_chooser() as fc_info:

                    media_btn = page.locator('button[aria-label*="multimedia"], button[aria-label*="Foto"]').first

                    await media_btn.click()

                file_chooser = await fc_info.value

                await file_chooser.set_files(abs_img)

                await page.wait_for_timeout(4000)

                next_btn = page.locator('button:has-text("Siguiente"), button:has-text("Next")').first

                if await next_btn.count() > 0:

                    await next_btn.click()

                    await page.wait_for_timeout(2000)

            # Rellenar texto

            editor = page.locator('div[role="textbox"]').first

            await editor.click()

            await editor.fill(text)

            await page.wait_for_timeout(2000)

            # Publicar

            publish_btn = page.locator('button:has-text("Publicar")').first

            await publish_btn.click()

            await page.wait_for_timeout(6000)

            # Inyectar primer comentario si se especificó con soporte para Tiptap / ProseMirror
            comment_status = "not_requested"
            if first_comment:
                try:
                    await page.wait_for_timeout(3000)
                    # En el feed, el post recién publicado está en la parte superior
                    comment_btn = page.locator('button[aria-label*="Comentar"], button:has-text("Comentar")').first
                    if await comment_btn.count() > 0:
                        try:
                            await comment_btn.click()
                            await page.wait_for_timeout(1500)
                        except Exception:
                            pass

                    # Selector resiliente para editor Tiptap / ProseMirror
                    comment_box = page.locator('div.tiptap.ProseMirror, div[role="textbox"][aria-label*="comentario"], div[role="textbox"][contenteditable="true"]').first
                    if await comment_box.count() == 0:
                        # Si no está en el feed, navegar a actividad reciente
                        act_url = await get_my_activity_url(page)
                        await page.goto(act_url, wait_until="commit")
                        await page.wait_for_timeout(3500)
                        comment_btn = page.locator('button[aria-label*="Comentar"], button:has-text("Comentar")').first
                        if await comment_btn.count() > 0:
                            await comment_btn.click()
                            await page.wait_for_timeout(1500)
                        comment_box = page.locator('div.tiptap.ProseMirror, div[role="textbox"][aria-label*="comentario"], div[role="textbox"][contenteditable="true"]').first

                    if await comment_box.count() > 0:
                        await comment_box.click()
                        # Inyección nativa multilínea para que Tiptap/ProseMirror genere bloques <p> y saltos reales
                        await page.keyboard.insert_text(first_comment)

                        await page.wait_for_timeout(1500)
                        submit_btn = page.locator('button.comments-comment-box__submit-button, button.hcbgmy, button:has-text("Comentar")').last
                        await submit_btn.click()
                        await page.wait_for_timeout(4000)

                        # Verificación en el DOM
                        content = await page.content()
                        fc_lines = [l.strip() for l in first_comment.split("\n") if l.strip()]
                        snippet = fc_lines[0][:25] if fc_lines else "http"
                        if snippet in content:
                            comment_status = "posted_and_verified"
                        else:
                            comment_status = "posted"
                    else:
                        comment_status = "box_not_found"
                except Exception as c_err:
                    print(f"[MCP Linkedin] Error publicando primer comentario: {c_err}")
                    comment_status = f"error: {c_err}"

            resolved_act_url = await get_my_activity_url(page)
            return {

                "status": "success",

                "message": "Publicación realizada con éxito en LinkedIn",

                "has_image": bool(image_path),

                "comment_status": comment_status,

                "profile_activity_url": resolved_act_url

            }

        finally:

            await browser.close()

@mcp.tool()

async def linkedin_get_recent_posts(limit: int = 5) -> list:

    """Extrae las publicaciones recientes del perfil con texto, enlaces canónicos e impresiones."""

    creds = get_creds()

    async with async_playwright() as p:

        browser, context = await get_browser_and_context(p)

        page = await context.new_page()

        try:

            await ensure_authenticated(page, creds)

            act_url = await get_my_activity_url(page)
            await page.goto(act_url, wait_until="commit")
            await page.wait_for_timeout(3500)

            posts_data = await page.evaluate(f'''() => {{
                const results = [];
                let buttons = Array.from(document.querySelectorAll(
                    'button[aria-label*="menú de controles"], button[aria-label*="controles"], button[aria-label*="opciones"], button.feed-shared-control-menu__trigger, button[aria-label*="More options"]'
                ));

                for (let i = 0; i < Math.min(buttons.length, {limit}); i++) {{

                    const btn = buttons[i];

                    let parent = btn.parentElement;

                    let card = null;

                    while (parent && parent.tagName !== 'MAIN' && parent.tagName !== 'BODY') {{

                        if (parent.querySelector('button[aria-label*="Reaccionar"], button[aria-label*="Comentar"]')) {{

                            card = parent;

                            break;

                        }}

                        parent = parent.parentElement;

                    }}

                    card = card || btn.closest('div');

                    const text = card ? card.innerText.trim() : '';

                    const links = card ? Array.from(card.querySelectorAll('a[href*="activity"], a[href*="update"], a[href*="analytics"], a[href*="/posts/"]')).map(a => a.href) : [];

                    let postUrl = links.find(l => l.includes('/posts/')) || links.find(l => l.includes('/feed/update/')) || links.find(l => l.includes('activity')) || '';

                    if (postUrl && postUrl.includes('analytics/post-summary/')) {{

                        const m = postUrl.match(/urn:li:activity:\\d+/);

                        if (m) postUrl = 'https://www.linkedin.com/feed/update/' + m[0] + '/';

                    }}

                    const impressionsEl = card ? card.querySelector('[aria-label*="impresiones"], [class*="views"]') : null;

                    results.push({{

                        index: i,

                        aria_label: btn.getAttribute('aria-label') || '',

                        post_url: postUrl.split('?')[0],

                        text: text.substring(0, 250) + (text.length > 250 ? '...' : ''),

                        impressions: impressionsEl ? impressionsEl.innerText.trim() : 'N/A'

                    }});

                }}

                return results;

            }}''')

            return posts_data

        finally:

            await browser.close()

@mcp.tool()

async def linkedin_toggle_feature_post(post_url: str = None, post_index: int = 0) -> dict:

    """Fija o retira un post de la sección de Destacados ('Destacar en la parte superior del perfil' / 'Quitar de destacados')."""

    creds = get_creds()

    async with async_playwright() as p:

        browser, context = await get_browser_and_context(p)

        page = await context.new_page()

        try:

            await ensure_authenticated(page, creds)

            await open_post_menu(page, post_url=post_url, post_index=post_index)

            item = page.locator('[role="menuitem"]:has-text("destacado"), [role="menuitem"]:has-text("Destacar")').first

            if await item.count() == 0:

                raise RuntimeError("No se encontró la opción de destacados en el menú")

            action_text = (await item.inner_text()).split("\n")[0].strip()

            await item.click()

            await page.wait_for_timeout(3000)

            return {

                "status": "success",

                "action_performed": action_text,

                "message": f"Acción '{action_text}' ejecutada con éxito."

            }

        finally:

            await browser.close()

@mcp.tool()

async def linkedin_toggle_save_post(post_url: str = None, post_index: int = 0) -> dict:

    """Guarda o desguarda un post en elementos guardados ('Guardar' / 'Quitar de guardados')."""

    creds = get_creds()

    async with async_playwright() as p:

        browser, context = await get_browser_and_context(p)

        page = await context.new_page()

        try:

            await ensure_authenticated(page, creds)

            await open_post_menu(page, post_url=post_url, post_index=post_index)

            item = page.locator('[role="menuitem"]:has-text("Guardar"), [role="menuitem"]:has-text("guardados")').first

            if await item.count() == 0:

                raise RuntimeError("No se encontró la opción de Guardar en el menú")

            action_text = (await item.inner_text()).split("\n")[0].strip()

            await item.click()

            await page.wait_for_timeout(3000)

            return {

                "status": "success",

                "action_performed": action_text,

                "message": f"Acción '{action_text}' ejecutada correctamente."

            }

        finally:

            await browser.close()

@mcp.tool()

async def linkedin_get_post_embed_code(post_url: str = None, post_index: int = 0) -> dict:

    """Extrae el código HTML <iframe> para incrustar la publicación en páginas web o blogs."""

    creds = get_creds()

    async with async_playwright() as p:

        browser, context = await get_browser_and_context(p)

        page = await context.new_page()

        try:

            await ensure_authenticated(page, creds)

            await open_post_menu(page, post_url=post_url, post_index=post_index)

            item = page.locator('[role="menuitem"]:has-text("Insertar esta publicación")').first

            if await item.count() == 0:

                raise RuntimeError("No se encontró 'Insertar esta publicación' en el menú")

            await item.click()

            await page.wait_for_timeout(2000)

            snippet_el = page.locator('textarea[id*="embed"], textarea').first

            if await snippet_el.count() == 0:

                raise RuntimeError("No se localizó el área de código de inserción en el modal")

            embed_html = await snippet_el.input_value()

            await page.keyboard.press("Escape")

            return {

                "status": "success",

                "embed_iframe_code": embed_html.strip()

            }

        finally:

            await browser.close()

@mcp.tool()

async def linkedin_get_post_link(post_url: str = None, post_index: int = 0) -> dict:

    """Obtiene el enlace canónico directo y limpio de una publicación."""

    if post_url:

        return {"status": "success", "post_url": post_url.split("?")[0]}

    creds = get_creds()

    async with async_playwright() as p:

        browser, context = await get_browser_and_context(p)

        page = await context.new_page()

        try:

            await ensure_authenticated(page, creds)

            act_url = await get_my_activity_url(page)
            await page.goto(act_url, wait_until="domcontentloaded")

            await page.wait_for_timeout(4000)

            resolved_url = await page.evaluate(f'''() => {{

                const buttons = document.querySelectorAll('button[aria-label*="menú de controles"], button[aria-label*="controles"], button[aria-label*="opciones"], button.feed-shared-control-menu__trigger');

                if (buttons.length > {post_index}) {{

                    const btn = buttons[{post_index}];

                    let parent = btn.parentElement;

                    while (parent && parent.tagName !== 'MAIN' && parent.tagName !== 'BODY') {{

                        const a = parent.querySelector('a[href*="/feed/update/"], a[href*="activity"]');

                        if (a) return a.href.split('?')[0];

                        parent = parent.parentElement;

                    }}

                }}

                return '';

            }}''')

            if not resolved_url:

                await open_post_menu(page, post_url=None, post_index=post_index)

                item = page.locator('[role="menuitem"]:has-text("Copiar enlace"), [role="menuitem"]:has-text("Copy link")').first

                if await item.count() > 0:

                    await item.click()

                    await page.wait_for_timeout(1000)

            return {

                "status": "success",

                "post_url": resolved_url or f"{act_url} (Post #{post_index})"

            }

        finally:

            await browser.close()

@mcp.tool()

async def linkedin_edit_post(new_text: str, post_url: str = None, post_index: int = 0) -> dict:

    """Edita el texto de una publicación existente ('Editar publicación')."""

    creds = get_creds()

    async with async_playwright() as p:

        browser, context = await get_browser_and_context(p)

        page = await context.new_page()

        try:

            await ensure_authenticated(page, creds)

            await open_post_menu(page, post_url=post_url, post_index=post_index)

            item = page.locator('[role="menuitem"]:has-text("Editar publicación")').first

            if await item.count() == 0:

                raise RuntimeError("No se encontró la opción 'Editar publicación' en el menú")

            await item.click()

            await page.wait_for_timeout(2000)

            editor = page.locator('div[role="textbox"]').first

            await editor.click()

            await editor.fill(new_text)

            await page.wait_for_timeout(1500)

            save_btn = page.locator('button:has-text("Guardar"), button:has-text("Save")').first

            await save_btn.click()

            await page.wait_for_timeout(4000)

            return {

                "status": "success",

                "message": "Publicación editada y guardada correctamente",

                "updated_text_preview": new_text[:100] + "..."

            }

        finally:

            await browser.close()

@mcp.tool()

async def linkedin_delete_post(confirm: bool = False, post_url: str = None, post_index: int = 0) -> dict:

    """Elimina permanentemente una publicación. Requiere confirm=True como salvaguarda obligatoria."""

    if not confirm:

        return {

            "status": "requires_confirmation",

            "message": "Para eliminar la publicación debes especificar confirm=True."

        }

    creds = get_creds()

    async with async_playwright() as p:

        browser, context = await get_browser_and_context(p)

        page = await context.new_page()

        try:

            await ensure_authenticated(page, creds)

            await open_post_menu(page, post_url=post_url, post_index=post_index)

            item = page.locator('[role="menuitem"]:has-text("Eliminar publicación")').first

            if await item.count() == 0:

                raise RuntimeError("No se encontró la opción 'Eliminar publicación' en el menú")

            await item.click()

            await page.wait_for_timeout(2000)

            confirm_btn = page.locator('button:has-text("Eliminar"), button:has-text("Delete")').last

            await confirm_btn.click()

            await page.wait_for_timeout(4000)

            return {

                "status": "success",

                "message": "Publicación eliminada permanentemente de LinkedIn."

            }

        finally:

            await browser.close()

@mcp.tool()

async def linkedin_get_comment_settings_url(post_url: str = None, post_index: int = 0) -> dict:

    """Obtiene la directriz y URL para configurar quién puede comentar ('¿Quién puede comentar esta publicación?')."""

    creds = get_creds()

    async with async_playwright() as p:

        browser, context = await get_browser_and_context(p)

        page = await context.new_page()

        try:

            await ensure_authenticated(page, creds)

            await open_post_menu(page, post_url=post_url, post_index=post_index)

            item = page.locator('[role="menuitem"]:has-text("comentar")').first

            href = await item.get_attribute("href") if await item.count() > 0 else "https://www.linkedin.com/sharing/commentControl"

            return {

                "status": "success",

                "comment_control_url": href or "https://www.linkedin.com/sharing/commentControl",

                "description": "LinkedIn permite configurar quién puede comentar mediante la página de privacidad de comentarios."
            }
        finally:
            await browser.close()

@mcp.tool()
async def linkedin_add_comment(
    post_url: str,
    comment_text: str,
    verify_author: str = None,
    verify_topic: str = None
) -> dict:
    """
    Publica un comentario estructurado en una publicación de LinkedIn con validación estricta de autoría y topic.
    Aplica inyección nativa multilínea (párrafos <p> en Tiptap) evitando el colapso de saltos de línea.
    
    Args:
        post_url: URL completa de la publicación en LinkedIn (https://www.linkedin.com/feed/update/urn:li:activity:...).
        comment_text: Texto completo del comentario con saltos de línea y viñetas.
        verify_author: (Opcional pero recomendado) Nombre del autor esperado en el post para evitar comentar en hilos ajenos.
        verify_topic: (Opcional) Texto o tema clave que debe contener la publicación.
    """
    creds = get_creds()
    async with async_playwright() as p:
        browser, context = await get_browser_and_context(p)
        page = await context.new_page()
        try:
            await ensure_authenticated(page, creds)
            await page.goto(post_url, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(3000)

            # Validación estricta de autoría y contenido
            content = await page.content()
            if verify_author and verify_author.lower() not in content.lower():
                return {
                    "status": "aborted",
                    "reason": f"El autor verificado '{verify_author}' no coincide con el contenido de la publicación.",
                    "url": post_url
                }
            if verify_topic and verify_topic.lower() not in content.lower():
                return {
                    "status": "aborted",
                    "reason": f"El tema clave '{verify_topic}' no fue encontrado en la publicación.",
                    "url": post_url
                }

            # Localizar caja de comentarios
            comment_box = page.locator('div.tiptap.ProseMirror, div[role="textbox"][aria-label*="comentario"], div[role="textbox"][contenteditable="true"]').first
            if await comment_box.count() == 0:
                comment_btn = page.locator('button[aria-label*="Comentar"], button:has-text("Comentar")').first
                if await comment_btn.count() > 0:
                    await comment_btn.click()
                    await page.wait_for_timeout(1000)
                comment_box = page.locator('div.tiptap.ProseMirror, div[role="textbox"][aria-label*="comentario"], div[role="textbox"][contenteditable="true"]').first

            if await comment_box.count() == 0:
                return {"status": "error", "message": "No se encontró el editor de comentarios de LinkedIn."}

            await comment_box.click()
            await page.wait_for_timeout(400)
            # Inyección nativa multilínea para párrafos <p> independientes
            await page.keyboard.insert_text(comment_text)
            await page.wait_for_timeout(1500)

            submit_btn = page.locator('button.comments-comment-box__submit-button, button.hcbgmy, button:has-text("Comentar"), button:has-text("Publicar")').last
            await submit_btn.click()
            await page.wait_for_timeout(4000)

            return {
                "status": "success",
                "message": "Comentario publicado exitosamente con formateo multilínea verificado.",
                "post_url": post_url
            }
        finally:
            await browser.close()

# ==========================================
# BÚSQUEDA Y PROSPECCIÓN (Gente, Empleos, etc.)
# ==========================================

@mcp.tool()

async def linkedin_search_people(keywords: str, location: str = None, limit: int = 10) -> list:

    """Busca profesionales y personas en LinkedIn por palabras clave (cargo, nombre, tecnología)."""

    creds = get_creds()

    query = f"{keywords} {location}".strip() if location else keywords

    url = f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(query)}"

    async with async_playwright() as p:

        browser, context = await get_browser_and_context(p)

        page = await context.new_page()

        try:

            await ensure_authenticated(page, creds)

            await page.goto(url, wait_until="commit")

            await page.wait_for_timeout(4000)

            results = await page.evaluate(f'''() => {{

                const items = [];

                const links = Array.from(document.querySelectorAll('a[href*="/in/"]'));

                const seen = new Set();

                for (const l of links) {{

                    const href = l.href.split('?')[0];

                    const fullText = l.innerText.trim();

                    if (fullText.length > 3 && !seen.has(href) && !href.endsWith('/in/')) {{

                        seen.add(href);

                        const parts = fullText.split('\\n').map(s => s.trim()).filter(s => s.length > 0);

                        const name = parts[0] ? parts[0].replace(/•.*/, '').trim() : '';

                        const degree = fullText.match(/[123]º/) ? fullText.match(/[123]º/)[0] : '';

                        const headline = parts[1] || '';

                        const loc = parts[2] || '';

                        items.push({{

                            name: name,

                            degree: degree,

                            headline: headline,

                            location: loc,

                            profile_url: href

                        }});

                    }}

                    if (items.length >= {limit}) break;

                }}

                return items;

            }}''')

            return results

        finally:

            await browser.close()

@mcp.tool()

async def linkedin_search_jobs(keywords: str, location: str = "Madrid", remote_only: bool = False, limit: int = 10) -> list:

    """Busca ofertas de empleo activas en LinkedIn con soporte para filtros de ubicación y remoto."""

    creds = get_creds()

    search_query = f"{keywords} en {location}" if location else keywords

    if remote_only:

        search_query += " remoto"

    async with async_playwright() as p:

        browser, context = await get_browser_and_context(p)

        page = await context.new_page()

        try:

            await ensure_authenticated(page, creds)

            await page.goto("https://www.linkedin.com/jobs/", wait_until="domcontentloaded")

            await page.wait_for_timeout(2500)

            search_input = page.locator('input[placeholder*="empleo"], input#jobs-search-box-keyword-id').first

            if await search_input.count() > 0:

                await search_input.fill(search_query)

                await search_input.press("Enter")

                await page.wait_for_timeout(4500)

            else:

                jobs_url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(keywords)}&location={quote_plus(location)}&origin=JOBS_HOME_SEARCH_BUTTON"

                await page.goto(jobs_url, wait_until="domcontentloaded")

                await page.wait_for_timeout(4000)

            jobs = await page.evaluate(f'''() => {{

                const items = [];

                const links = Array.from(document.querySelectorAll('a[href*="/jobs/view/"], a[href*="currentJobId="]'));

                const seen = new Set();

                for (const l of links) {{

                    const url = l.href.split('?')[0];

                    if (!seen.has(url)) {{

                        seen.add(url);

                        const title = l.innerText.trim().split('\\n')[0];

                        if (title.length > 2 && !title.toLowerCase().includes('más') && !title.toLowerCase().includes('empleos')) {{

                            let parent = l.parentElement;

                            let companyText = '';

                            let locText = '';

                            while (parent && parent.tagName !== 'UL' && parent.tagName !== 'MAIN') {{

                                const cEl = parent.querySelector('h4, .job-card-container__company-name, .artdeco-entity-lockup__subtitle, [class*="company"]');

                                if (cEl && !companyText) companyText = cEl.innerText.trim();

                                const lEl = parent.querySelector('.job-card-container__metadata-item, .artdeco-entity-lockup__caption, [class*="location"]');

                                if (lEl && !locText) locText = lEl.innerText.trim();

                                if (companyText && locText) break;

                                parent = parent.parentElement;

                            }}

                            items.push({{

                                title: title,

                                company: companyText || 'Empresa en LinkedIn',

                                location: locText || '{location}',

                                job_url: url

                            }});

                        }}

                    }}

                    if (items.length >= {limit}) break;

                }}

                return items;

            }}''')

            return jobs

        finally:

            await browser.close()

@mcp.tool()

async def linkedin_search_companies(keywords: str, limit: int = 10) -> list:

    """Busca empresas e instituciones en LinkedIn por palabras clave."""

    creds = get_creds()

    url = f"https://www.linkedin.com/search/results/companies/?keywords={quote_plus(keywords)}"

    async with async_playwright() as p:

        browser, context = await get_browser_and_context(p)

        page = await context.new_page()

        try:

            await ensure_authenticated(page, creds)

            await page.goto(url, wait_until="commit")

            await page.wait_for_timeout(4000)

            companies = await page.evaluate(f'''() => {{

                const items = [];

                const links = document.querySelectorAll('a[href*="/company/"]');

                const seen = new Set();

                links.forEach(l => {{

                    const href = l.href.split('?')[0];

                    const fullText = l.innerText.trim();

                    if (fullText.length > 2 && !seen.has(href) && !href.endsWith('/company/')) {{

                        seen.add(href);

                        const parts = fullText.split('\\n').map(s => s.trim()).filter(s => s.length > 0);

                        items.push({{

                            name: parts[0] || '',

                            url: href,

                            details: parts[1] || ''

                        }});

                    }}

                }});

                return items.slice(0, {limit});

            }}''')

            return companies

        finally:

            await browser.close()

@mcp.tool()

async def linkedin_check_session() -> dict:

    """Valida la salud de la sesión activa en LinkedIn."""

    creds = get_creds()

    async with async_playwright() as p:

        browser, context = await get_browser_and_context(p)

        page = await context.new_page()

        try:

            await ensure_authenticated(page, creds)

            user_title = await page.title()

            return {

                "status": "active",

                "url": page.url,

                "title": user_title,

                "engine": "Brave Browser" if os.path.exists(BRAVE_PATH) else "Chromium",

                "storage_state_active": STORAGE_STATE_FILE.exists()

            }

        finally:

            await browser.close()

@mcp.tool()

async def linkedin_renew_session_interactive(timeout_sec: int = 180) -> dict:

    """

    Plan B Interactivo: Despliega una ventana física visible de Brave Browser en el escritorio

    del usuario (WinSta0\\Default) vía schtasks /IT para introducir credenciales, resolver captchas o 2FA.

    """

    success = trigger_interactive_session_renewal(timeout_sec=timeout_sec)

    if success:

        return {

            "status": "success",

            "message": "Sesión renovada interactivamente con éxito en Brave Browser. Cookies y almacenamiento actualizados.",

            "storage_state_active": STORAGE_STATE_FILE.exists()

        }

    else:

        return {

            "status": "failed",

            "message": f"Tiempo de espera agotado ({timeout_sec}s) o la sesión interactiva no alcanzó el feed de LinkedIn."

        }



# ==============================================================================
# HERRAMIENTAS INTEGRADAS DE OPEN-SOURCE (STICKERDANIEL & ELIASBIONDO)
# ==============================================================================

@mcp.tool()
async def linkedin_get_inbox_messages(limit: int = 10, unread_only: bool = False) -> dict:
    """
    Consulta la bandeja de entrada de mensajes de LinkedIn (/messaging/).
    Extrae remitentes, extracto del último mensaje, marcas temporales y estado de lectura.
    Inspirado en stickerdaniel/linkedin-mcp-server con salvaguardas de ritmo humano.
    """
    creds = get_creds()
    async with async_playwright() as p:
        browser, context = await get_browser_and_context(p)
        page = await context.new_page()
        try:
            await ensure_authenticated(page, creds)
            return await le.extract_inbox_messages(page, limit=limit, unread_only=unread_only)
        finally:
            await browser.close()

@mcp.tool()
async def linkedin_get_conversation_thread(thread_id_or_index: str, limit: int = 20) -> dict:
    """
    Obtiene el historial completo de mensajes de un chat o conversación específica.
    Acepta un índice de conversación, nombre del contacto o ID/URL del hilo (/messaging/thread/<id>/).
    """
    creds = get_creds()
    async with async_playwright() as p:
        browser, context = await get_browser_and_context(p)
        page = await context.new_page()
        try:
            await ensure_authenticated(page, creds)
            return await le.extract_conversation_thread(page, thread_id_or_index=thread_id_or_index, limit=limit)
        finally:
            await browser.close()

@mcp.tool()
async def linkedin_send_message(recipient_or_thread: str, message_text: str, confirm: bool = False) -> dict:
    """
    Envía un mensaje directo a un contacto o hilo en LinkedIn.
    SALVAGUARDA: Requiere confirm=True para ejecutar el envío real.
    Si confirm=False, devuelve una vista previa estructurada del borrador para validación del usuario.
    """
    if not confirm:
        return {
            "status": "draft_preview",
            "warning": "SALVAGUARDA ACTIVADA: El mensaje no ha sido enviado. Revisa el borrador y vuelve a llamar con confirm=True para emitirlo.",
            "recipient_or_thread": recipient_or_thread,
            "message_text": message_text
        }
    creds = get_creds()
    async with async_playwright() as p:
        browser, context = await get_browser_and_context(p)
        page = await context.new_page()
        try:
            await ensure_authenticated(page, creds)
            return await le.send_direct_message(page, recipient_or_thread=recipient_or_thread, message_text=message_text)
        finally:
            await browser.close()

@mcp.tool()
async def linkedin_get_profile_details(profile_url_or_username: str = "me") -> dict:
    """
    Extrae la información profunda y exhaustiva de un perfil de LinkedIn en JSON estructurado.
    Incluye: Nombre, Titular, Ubicación, Acerca de (About), Experiencias laborales con fechas/duraciones,
    Educación, Habilidades (Skills), Destacados y Actividad reciente.
    Inspirado en eliasbiondo/linkedin-mcp-server con BeautifulSoup resiliente.
    """
    creds = get_creds()
    async with async_playwright() as p:
        browser, context = await get_browser_and_context(p)
        page = await context.new_page()
        try:
            await ensure_authenticated(page, creds)
            return await le.extract_profile_details(page, profile_url_or_username=profile_url_or_username)
        finally:
            await browser.close()

@mcp.tool()
async def linkedin_get_feed_posts(limit: int = 10) -> dict:
    """
    Extrae publicaciones activas del feed global de LinkedIn (/feed/).
    Devuelve autor, titular del autor, texto de la publicación y conteo de reacciones.
    Inspirado en eliasbiondo/linkedin-mcp-server con protección de scroll humano.
    """
    creds = get_creds()
    async with async_playwright() as p:
        browser, context = await get_browser_and_context(p)
        page = await context.new_page()
        try:
            await ensure_authenticated(page, creds)
            return await le.extract_feed_posts(page, limit=limit)
        finally:
            await browser.close()

@mcp.tool()
async def linkedin_get_job_details(job_url_or_id: str) -> dict:
    """
    Extrae la descripción completa y requisitos de una oferta de empleo a partir de su ID o URL.
    Incluye: Título, Empresa, Ubicación, Modalidad (remoto/híbrido/presencial) y cuerpo completo de la descripción.
    """
    creds = get_creds()
    async with async_playwright() as p:
        browser, context = await get_browser_and_context(p)
        page = await context.new_page()
        try:
            await ensure_authenticated(page, creds)
            return await le.extract_job_details(page, job_url_or_id=job_url_or_id)
        finally:
            await browser.close()

@mcp.tool()
async def linkedin_get_company_details(company_url_or_slug: str) -> dict:
    """
    Extrae los detalles corporativos e institucionales completos de una empresa u organización.
    Incluye: Nombre, Resumen institucional, Sitio web, Sector/Industria, Tamaño y Sede.
    """
    creds = get_creds()
    async with async_playwright() as p:
        browser, context = await get_browser_and_context(p)
        page = await context.new_page()
        try:
            await ensure_authenticated(page, creds)
            return await le.extract_company_details(page, company_url_or_slug=company_url_or_slug)
        finally:
            await browser.close()

# ==============================================================================
# HERRAMIENTAS DE INTELIGENCIA EDITORIAL, ESTRATEGIA Y HEURÍSTICA ANTI-IA
# (Inspiradas en el benchmark Jakeschincariol/linkedin-agent-skill)
# ==============================================================================

@mcp.tool()
async def linkedin_humanize(text: str) -> dict:
    """
    Limpia el texto en 3 pasadas eliminando la huella sintética de IA:
    1. Caracteres invisibles (zero-width, BOMs, formato).
    2. Tipografía no estándar (em-dashes a comas, comillas curvas a rectas).
    3. Sustitución de 113+ términos corporativos trillados (slop) por lenguaje natural.
    Alerta además sobre estructuras sospechosas sin alterarlas automáticamente.
    """
    cleaned, report = li.humanize_text(text)
    return {
        "cleaned_text": cleaned,
        "report": report
    }

@mcp.tool()
async def linkedin_detect_ai(text: str) -> dict:
    """
    Evalúa el texto mediante un panel heurístico local de 5 verificaciones:
    BURSTINESS (variación de longitud de oraciones), SPECIFICITY (densidad de números y nombres),
    SLOP DENSITY (frecuencia de términos cliché), FINGERPRINT (caracteres no generados por teclado humano),
    y VOICE (contracciones, pronombres personales y estructuras IA).
    Devuelve puntuación humana (0-100) y veredicto ('PASS', 'REVIEW', 'FLAGGED').
    """
    return li.detect_ai_markers(text)

@mcp.tool()
async def linkedin_hook_score(text: str, formula_id: int = None) -> dict:
    """
    Analiza el gancho (líneas 1 y 2) de un post de LinkedIn contra las 21 fórmulas probadas (hooks.json).
    Verifica la visibilidad antes del corte de 'Ver más' (140 car en móvil, 210 en escritorio)
    y detecta trampas habituales (falta de números, preguntas genéricas, etc.).
    """
    return li.score_hook(text, formula_id=formula_id)

@mcp.tool()
async def linkedin_score_profile(profile_url_or_username: str = "me") -> dict:
    """
    Audita un perfil de LinkedIn frente a la rúbrica objetiva de 12 elementos (100 puntos totales).
    Extrae los datos en vivo del perfil (vía navegador o CDP) y emite puntuación global,
    diagnóstico por sección y plan de acción prioritario 'Fix-First'.
    """
    details = await linkedin_get_profile_details(profile_url_or_username=profile_url_or_username)
    rubric_eval = li.score_profile_rubric(details)
    return {
        "profile_evaluated": profile_url_or_username,
        "profile_name": details.get("name", ""),
        "headline": details.get("headline", ""),
        **rubric_eval
    }

@mcp.tool()
async def linkedin_generate_comment(post_text: str, comment_type: int = None, author_name: str = None) -> dict:
    """
    Genera propuestas de comentarios de alto valor basadas en 9 arquetipos profesionales:
    1. Añadir dato, 2. Caso faltante, 3. Desacuerdo respetuoso, 4. Extender una línea,
    5. Pregunta incisiva, 6. El recibo / prueba, 7. Corrección constructiva, 8. Reencuadre, 9. Frase contundente.
    Prohíbe comentarios genéricos vacíos ('¡Gran post!').
    """
    return li.generate_comment_options(post_text, comment_type=comment_type, author_name=author_name)

@mcp.tool()
async def linkedin_triage_inbox(limit: int = 10, unread_only: bool = False) -> dict:
    """
    Extrae las conversaciones de la bandeja de entrada (/messaging/) y las clasifica automáticamente en:
    LEAD (clientes potenciales), RECRUITER (ofertas laborales), PEER (networking genuino),
    ASK (peticiones de favores/dudas) y SPAM (secuencias automatizadas de prospección en frío con enlaces a calendario).
    """
    inbox_data = await linkedin_get_inbox_messages(limit=limit, unread_only=unread_only)
    convs = inbox_data.get("conversations", [])
    triage_res = li.triage_inbox_conversations(convs)
    return {
        "inbox_total": inbox_data.get("total_found", len(convs)),
        **triage_res
    }

@mcp.tool()
async def linkedin_triage_replies(comments: list) -> dict:
    """
    Clasifica los comentarios recibidos bajo una publicación propia en 5 niveles estratégicos:
    LEAD (potencial cliente), SUBSTANCE (argumentación o desacuerdo), PEER (contacto relevante),
    SUPPORT (reacciones y felicitaciones) y NOISE (spam/irrelevante).
    Prioriza las respuestas para maximizar el alcance en la primera hora.
    """
    return li.triage_post_replies(comments)

@mcp.tool()
async def linkedin_carousel_planner(topic: str, num_slides: int = 10) -> dict:
    """
    Diseña la arquitectura diapositiva a diapositiva de un post documental (carrusel PDF 1080x1350, ratio 4:5).
    Incluye reglas de menos de 25 palabras por slide, diapositiva de recapitulación y plantilla HTML/CSS para imprimir a PDF.
    """
    return li.plan_carousel_deck(topic=topic, num_slides=num_slides)

@mcp.tool()
async def linkedin_repurpose_content(source_text: str) -> dict:
    """
    Desglosa un contenido largo (artículo, vídeo, transcripción o llamada) en elementos atómicos:
    afirmaciones polémicas, cifras clave, historias, mecanismos de acción, errores y frases destacadas.
    Genera una propuesta de calendario semanal de 4 publicaciones con fórmulas de ganchos asignadas.
    """
    return li.repurpose_asset(source_text=source_text)

@mcp.tool()
async def linkedin_dm_sequence(name: str, hook_reason: str, offer_goal: str = "") -> dict:
    """
    Genera una secuencia de mensajería directa en 4 fases respetando el límite de LinkedIn:
    1. Nota de invitación (estrictamente <= 200 caracteres, sin pedir nada).
    2. Primer mensaje (+1 día tras aceptar, aportando valor).
    3. Seguimiento 1 (+4 días, con recurso adicional).
    4. Seguimiento 2 (+10 días, cierre de ciclo sin presión).
    """
    return li.generate_dm_sequence(name=name, hook_reason=hook_reason, offer_goal=offer_goal)

def main():
    """Punto de entrada de consola para iniciar el servidor MCP."""
    mcp.run()

if __name__ == "__main__":
    main()


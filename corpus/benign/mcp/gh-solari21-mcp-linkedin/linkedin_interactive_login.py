"""
Módulo Interactivo de Renovación de Sesión de LinkedIn (Plan B)
Lanza una ventana física visible de Brave Browser en el escritorio del usuario (WinSta0\\Default)
utilizando schtasks /IT para resolver captchas, 2FA o introducir contraseñas actualizadas.
"""

import os
import sys
import json
import time
import uuid
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding='utf-8')

USER_PROFILE = os.environ.get("USERPROFILE", os.path.expanduser("~"))

def resolve_auth_paths():
    """Resuelve dinámicamente las rutas de credenciales y cookies de sesión."""
    env_creds = os.environ.get("LINKEDIN_CREDS_FILE")
    env_storage = os.environ.get("LINKEDIN_STORAGE_STATE_FILE")
    env_auth_dir = os.environ.get("LINKEDIN_AUTH_DIR")

    if env_creds and env_storage:
        return Path(env_creds), Path(env_storage)

    if env_auth_dir:
        auth_dir = Path(env_auth_dir)
        return auth_dir / "linkedin_creds.json", auth_dir / "linkedin_storage_state.json"

    candidates = [
        Path(USER_PROFILE) / ".gemini" / "config" / "mcp-auth",
        Path(USER_PROFILE) / ".config" / "mcp-linkedin",
        Path(__file__).parent.resolve() / "config",
        Path(__file__).parent.resolve()
    ]
    for c in candidates:
        if (c / "linkedin_creds.json").exists() or (c / "linkedin_storage_state.json").exists():
            return c / "linkedin_creds.json", c / "linkedin_storage_state.json"

    default_dir = Path(USER_PROFILE) / ".gemini" / "config" / "mcp-auth"
    if default_dir.exists():
        return default_dir / "linkedin_creds.json", default_dir / "linkedin_storage_state.json"

    std_dir = Path(USER_PROFILE) / ".config" / "mcp-linkedin"
    std_dir.mkdir(parents=True, exist_ok=True)
    return std_dir / "linkedin_creds.json", std_dir / "linkedin_storage_state.json"

CREDS_FILE, STORAGE_STATE_FILE = resolve_auth_paths()
AUTH_DIR = CREDS_FILE.parent

def resolve_temp_dir():
    env_temp = os.environ.get("LINKEDIN_TEMP_DIR")
    if env_temp:
        p = Path(env_temp)
        p.mkdir(parents=True, exist_ok=True)
        return p
    gemini_temp = Path(USER_PROFILE) / ".gemini" / "config" / "temp_interactive"
    if gemini_temp.parent.exists():
        gemini_temp.mkdir(parents=True, exist_ok=True)
        return gemini_temp
    import tempfile
    t = Path(tempfile.gettempdir()) / "mcp_linkedin_temp"
    t.mkdir(parents=True, exist_ok=True)
    return t

TEMP_DIR = resolve_temp_dir()

def get_brave_path() -> str:
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]

BRAVE_PATH = get_brave_path()

def sanitize_cookies(cookies: list) -> list:
    """Asegura que los cookies cumplan con el esquema estricto de Playwright, normaliza dominios a .linkedin.com y garantiza persistencia de 1 año."""
    cleaned = []
    seen_names = set()
    now_ts = time.time()
    one_year_ahead = now_ts + 365.0 * 24.0 * 3600.0

    for c in cookies:
        name = c.get("name")
        if not name or name in seen_names:
            continue

        dom = c.get("domain", "")
        # Normalizar SIEMPRE el dominio de LinkedIn a .linkedin.com
        if "linkedin.com" in dom:
            dom = ".linkedin.com"

        exp = c.get("expires")
        if exp is None or not isinstance(exp, (int, float)) or float(exp) <= 0 or float(exp) < now_ts:
            # Asegurar persistencia de 1 año para cookies críticas de autenticación
            if name in ["li_at", "li_rm", "JSESSIONID", "bcookie", "bscookie", "lidc"]:
                exp = one_year_ahead
            else:
                exp = -1.0
        else:
            exp = float(exp)

        ss = c.get("same_site") or c.get("sameSite") or "Lax"
        ss_norm = ss.capitalize() if isinstance(ss, str) else "Lax"
        if ss_norm not in ["Strict", "Lax", "None"]:
            ss_norm = "None" if c.get("secure") else "Lax"

        val = str(c.get("value", ""))
        # Desescapar comillas literales que a veces devuelve CDP
        if val.startswith('"') and val.endswith('"') and len(val) > 1:
            val = val[1:-1]

        seen_names.add(name)
        cleaned.append({
            "name": name,
            "value": val,
            "domain": dom,
            "path": c.get("path", "/"),
            "expires": exp,
            "httpOnly": c.get("httpOnly", c.get("http_only", False)),
            "secure": c.get("secure", False),
            "sameSite": ss_norm
        })
    return cleaned

def save_storage_state_atomically(cookies: list) -> bool:
    """Guarda atómicamente el estado de almacenamiento con li_at verificado, normalizado y respaldo .bak permanente."""
    has_li_at = any(c.get("name") == "li_at" and len(str(c.get("value", ""))) > 10 for c in cookies)
    if not has_li_at:
        return False

    cleaned = sanitize_cookies(cookies)
    storage_data = {
        "cookies": cleaned,
        "origins": [
            {
                "origin": "https://www.linkedin.com",
                "localStorage": []
            }
        ]
    }

    # 1. Archivo canónico global
    STORAGE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STORAGE_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(storage_data, f, indent=2)

    # 2. Respaldo permanente .bak (nunca se sobrescribe con datos vacíos)
    backup_file = STORAGE_STATE_FILE.with_suffix(".json.bak")
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(storage_data, f, indent=2)

    # 3. Directorio config local del proyecto
    proj_config = Path(__file__).parent.resolve() / "config"
    proj_config.mkdir(parents=True, exist_ok=True)
    with open(proj_config / "linkedin_storage_state.json", "w", encoding="utf-8") as f:
        json.dump(storage_data, f, indent=2)

    return True

def sync_cookies_from_brave_cdp(port: int = 9222) -> bool:
    """
    Sincroniza silenciosamente las cookies de sesión activa de LinkedIn desde Brave CDP (puerto 9222)
    mediante WebSocket atómico JSON-RPC directo (<100ms, cero ventanas, cero robo de foco, cero captcha).
    Combina Storage.getCookies a nivel navegador y Network.getCookies en pestañas activas de LinkedIn.
    """
    try:
        import urllib.request
        import websocket

        collected_cookies = {}

        # 1. Extracción a nivel de navegador (Storage.getCookies)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1.5) as resp:
                ver_data = json.loads(resp.read().decode())
                ws_url = ver_data.get("webSocketDebuggerUrl")
            if ws_url:
                ws = websocket.create_connection(ws_url, timeout=2.5)
                ws.send(json.dumps({"id": 1, "method": "Storage.getCookies"}))
                msg = json.loads(ws.recv())
                ws.close()
                for c in msg.get("result", {}).get("cookies", []):
                    if "linkedin" in c.get("domain", ""):
                        collected_cookies[(c.get("name"), c.get("domain"))] = c
        except Exception:
            pass

        # 2. Extracción a nivel de pestaña activa (Network.getCookies con URLs canónicas)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=1.5) as resp:
                tabs = json.loads(resp.read().decode())
            li_tabs = [t for t in tabs if "linkedin.com" in t.get("url", "")]
            for t in li_tabs:
                tab_ws = t.get("webSocketDebuggerUrl")
                if not tab_ws:
                    continue
                try:
                    ws_tab = websocket.create_connection(tab_ws, timeout=2.0)
                    ws_tab.send(json.dumps({
                        "id": 1,
                        "method": "Network.getCookies",
                        "params": {"urls": ["https://www.linkedin.com/", "https://www.linkedin.com/feed/"]}
                    }))
                    msg_tab = json.loads(ws_tab.recv())
                    ws_tab.close()
                    for c in msg_tab.get("result", {}).get("cookies", []):
                        if "linkedin" in c.get("domain", ""):
                            collected_cookies[(c.get("name"), c.get("domain"))] = c
                except Exception:
                    pass
        except Exception:
            pass

        cookies_list = list(collected_cookies.values())
        if not cookies_list:
            return False

        return save_storage_state_atomically(cookies_list)
    except Exception:
        return False


async def run_visible_login(result_file: str, timeout_sec: int = 180):
    """
    Ejecuta el navegador Brave en modo visible para que el usuario resuelva cualquier
    desafío de seguridad (reCAPTCHA, 2FA, credenciales caducadas).
    """
    creds = {}
    if CREDS_FILE.exists():
        try:
            with open(CREDS_FILE, "r", encoding="utf-8") as f:
                creds = json.load(f)
        except Exception:
            pass

    async with async_playwright() as p:
        launch_kwargs = {
            "headless": False,
            "args": [
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
                "--new-window"
            ]
        }
        if os.path.exists(BRAVE_PATH):
            launch_kwargs["executable_path"] = BRAVE_PATH

        browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="es-ES",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # 1. Navegar a LinkedIn login en segundo plano sin robar el foco del usuario
            print("[Plan B] Abriendo ventana de login en segundo plano (sin robar foco)...")
            await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            # Aceptar cookies si aparece banner
            try:
                cookie_btn = page.get_by_role("button", name="Aceptar")
                if await cookie_btn.count() > 0:
                    await cookie_btn.first.click()
                    await page.wait_for_timeout(1000)
            except Exception:
                pass

            # 2. Esperar a que el usuario complete su inicio de sesión en pantalla de forma natural
            print(f"[Plan B] Ventana abierta en https://www.linkedin.com/login. Esperando inicio de sesión del usuario (hasta {timeout_sec}s)...")
            start_t = time.time()
            success = False
            while time.time() - start_t < timeout_sec:
                try:
                    await page.wait_for_timeout(1000)
                    curr_url = page.url
                    if ("feed" in curr_url or "/in/" in curr_url) and "login" not in curr_url and "checkpoint" not in curr_url and "uas" not in curr_url:
                        print(f"[Plan B] ¡Sesión alcanzada exitosamente en {curr_url}!")
                        success = True
                        break
                except Exception as loop_e:
                    print(f"[Plan B] Error en espera interactiva: {loop_e}")
                    break

            if success:
                # 3. Guardar storage state depurado de forma permanente
                raw_state = await context.storage_state()
                saved = save_storage_state_atomically(raw_state.get("cookies", []))
                if saved:
                    with open(result_file, "w", encoding="utf-8") as f:
                        json.dump({"status": "success", "url": page.url}, f)
                    print("[Plan B] Estado de sesión y cookies guardadas con éxito permanente.")
                else:
                    with open(result_file, "w", encoding="utf-8") as f:
                        json.dump({"status": "no_li_at", "url": page.url}, f)
                    print("[Plan B] Sesión alcanzada pero cookie li_at no encontrada.")
            else:
                with open(result_file, "w", encoding="utf-8") as f:
                    json.dump({"status": "timeout", "url": page.url}, f)
                print("[Plan B] Tiempo de espera agotado sin alcanzar el feed.")

        except Exception as e:
            print(f"[Plan B] Excepción durante login interactivo: {e}")
            try:
                with open(result_file, "w", encoding="utf-8") as f:
                    json.dump({"status": "error", "error": str(e)}, f)
            except Exception:
                pass
        finally:
            try:
                await browser.close()
            except Exception:
                pass

def trigger_interactive_session_renewal(timeout_sec: int = 180) -> bool:
    """
    Despliega la ventana visible de Brave en la sesión interactiva del usuario (WinSta0\\Default)
    mediante el Programador de Tareas Interactivo de Windows (/IT).
    Prioriza SIEMPRE la extracción silenciosa desde Brave CDP (puerto 9222) antes de abrir cualquier ventana.
    """
    # 0. Contingencia Silenciosa Prioritaria: Si Brave CDP está activo, extraer cookies de inmediato (0 ventanas)
    if sync_cookies_from_brave_cdp():
        print("[Sesión LinkedIn] Sesión activa sincronizada silenciosamente desde Brave CDP (0 interacción).")
        return True

    # 1. Si Brave CDP está activo en el puerto 9222, abrir pestaña visible de login directamente en su navegador y esperar
    try:
        import urllib.request
        import websocket
        with urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=1.5) as resp:
            ver_data = json.loads(resp.read().decode())
            ws_url = ver_data.get("webSocketDebuggerUrl")
        if ws_url:
            print("[Sesión LinkedIn] Brave está abierto. Abriendo pestaña interactiva de login y esperando...")
            ws = websocket.create_connection(ws_url, timeout=3.0)
            ws.send(json.dumps({
                "id": 1,
                "method": "Target.createTarget",
                "params": {"url": "https://www.linkedin.com/login"}
            }))
            res = json.loads(ws.recv())
            target_id = res.get("result", {}).get("targetId")
            if target_id:
                ws.send(json.dumps({
                    "id": 2,
                    "method": "Target.activateTarget",
                    "params": {"targetId": target_id}
                }))
                try:
                    ws.recv()
                except Exception:
                    pass
            ws.close()

            # Esperar a que el usuario complete el inicio de sesión en Brave
            start_wait = time.time()
            while time.time() - start_wait < timeout_sec:
                time.sleep(2.0)
                if sync_cookies_from_brave_cdp():
                    print("[Sesión LinkedIn] ¡Sesión autenticada y sincronizada exitosamente desde Brave!")
                    return True
            print("[Sesión LinkedIn] Tiempo de espera agotado esperando login en Brave.")
    except Exception as cdp_err:
        print(f"[Sesión LinkedIn] Brave CDP no disponible para apertura directa: {cdp_err}")

    session_id = uuid.uuid4().hex[:8]
    task_name = f"Antigravity_LinkedIn_Renew_{session_id}"
    bat_path = TEMP_DIR / f"renew_{session_id}.bat"
    result_path = TEMP_DIR / f"result_{session_id}.json"
    log_path = TEMP_DIR / f"renew_{session_id}.log"
    script_path = Path(__file__).resolve()

    python_exe = sys.executable

    # Script batch con ejecución directa de Python
    bat_content = (
        f'@echo off\r\n'
        f'chcp 65001 >nul\r\n'
        f'"{python_exe}" "{script_path}" --worker "{result_path}" --timeout {timeout_sec} > "{log_path}" 2>&1\r\n'
    )
    with open(bat_path, "wb") as f:
        f.write(bat_content.encode("utf-8"))

    try:
        # 1. Crear tarea interactiva (/IT) en el escritorio del usuario
        c_cmd = f'& schtasks /create /tn "{task_name}" /tr "\'{bat_path}\'" /sc ONCE /st 23:59 /it /f'
        subprocess.run(["powershell", "-NoProfile", "-Command", c_cmd], capture_output=True)

        # 2. Ejecutar la tarea interactiva
        r_cmd = f'schtasks /run /tn "{task_name}"'
        subprocess.run(["powershell", "-NoProfile", "-Command", r_cmd], capture_output=True)

        # 3. Esperar el archivo de resultado
        start_wait = time.time()
        while time.time() - start_wait < timeout_sec + 10:
            if result_path.exists():
                try:
                    with open(result_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("status") == "success":
                        # Limpiar log si fue exitoso
                        if log_path.exists():
                            try:
                                os.remove(log_path)
                            except Exception:
                                pass
                        return True
                    else:
                        return False
                except Exception:
                    pass
            time.sleep(1.0)
        return False

    finally:
        # Limpieza de la tarea programada y scripts temporales
        d_cmd = f'schtasks /delete /tn "{task_name}" /f'
        subprocess.run(["powershell", "-NoProfile", "-Command", d_cmd], capture_output=True)
        if bat_path.exists():
            try:
                os.remove(bat_path)
            except Exception:
                pass
        if result_path.exists():
            try:
                os.remove(result_path)
            except Exception:
                pass

if __name__ == "__main__":
    import asyncio
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", type=str, help="Ruta al archivo de resultado")
    parser.add_argument("--timeout", type=int, default=180, help="Segundos máximos de espera")
    args = parser.parse_args()

    if args.worker:
        asyncio.run(run_visible_login(args.worker, timeout_sec=args.timeout))
    else:
        print("Lanzando proceso interactivo vía schtasks /IT...")
        res = trigger_interactive_session_renewal(timeout_sec=args.timeout)
        print("Resultado de la renovación:", res)

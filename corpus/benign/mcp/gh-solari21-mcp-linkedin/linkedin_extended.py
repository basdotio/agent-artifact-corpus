"""
Módulo de Capacidades Extendidas de LinkedIn (MCP Linkedin).
Integra las mejores prácticas y funcionalidades de stickerdaniel/linkedin-mcp-server
y eliasbiondo/linkedin-mcp-server, adaptadas al DOM actual de LinkedIn con
salvaguardas anti-ban y ejecución 100% en Brave Browser.
"""

import os
import re
import json
import asyncio
import random
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

async def human_delay(min_s: float = 1.5, max_s: float = 3.0):
    """Introduce una pausa con jitter aleatorio para imitar el ritmo de navegación humano."""
    delay = random.uniform(min_s, max_s)
    await asyncio.sleep(delay)

async def extract_inbox_messages(page, limit: int = 10, unread_only: bool = False) -> Dict[str, Any]:
    """
    Extrae la lista de conversaciones recientes de la bandeja de entrada (/messaging/).
    Inspirado en stickerdaniel/linkedin-mcp-server.
    """
    await human_delay(1.0, 2.0)
    await page.goto("https://www.linkedin.com/messaging/", wait_until="domcontentloaded")
    await page.wait_for_selector("main", timeout=15000)
    await asyncio.sleep(2.5)

    convs = await page.evaluate('''() => {
        const results = [];
        const items = document.querySelectorAll('main li.msg-conversation-listitem, main li[class*="msg-conversations"]');
        const list = items.length > 0 ? items : document.querySelectorAll('main li');
        
        for (let i = 0; i < list.length; i++) {
            const li = list[i];
            const text = (li.innerText || '').trim();
            if (!text || text.length < 8) continue;
            
            // Buscar enlace al hilo
            const a = li.querySelector('a[href*="/messaging/thread/"]');
            const href = a ? a.getAttribute('href') : '';
            let threadId = '';
            if (href) {
                const m = href.match(/\\/messaging\\/thread\\/([^/?#]+)/);
                if (m) threadId = m[1];
            }
            
            // Detección de no leído
            const isUnread = !!li.querySelector('.msg-conversation-card__unread-count, [class*="unread"]');
            
            // Participante
            const nameEl = li.querySelector('h3, [class*="participant-names"], [class*="participant"], [class*="name"]');
            let name = nameEl ? nameEl.innerText.trim() : '';
            if (!name) {
                // Fallback: extraer primera línea relevante
                const parts = text.split('\\n').map(p => p.trim()).filter(Boolean);
                if (parts.length > 0 && !parts[0].startsWith('Estado')) {
                    name = parts[0];
                } else if (parts.length > 1) {
                    name = parts[1];
                }
            }
            
            // Snippet
            const snippetEl = li.querySelector('p, [class*="snippet"], [class*="message-snippet"]');
            let snippet = snippetEl ? snippetEl.innerText.trim() : '';
            
            // Timestamp
            const timeEl = li.querySelector('time, [class*="time"], [class*="date"]');
            let timeStr = timeEl ? timeEl.innerText.trim() : '';
            
            results.push({
                index: results.length,
                participant_name: name,
                thread_id: threadId,
                href: href ? (href.startsWith('http') ? href : `https://www.linkedin.com${href}`) : '',
                is_unread: isUnread,
                last_message: snippet,
                timestamp: timeStr,
                summary: text.slice(0, 150).replace(/\\n+/g, ' | ')
            });
        }
        return results;
    }''')

    if unread_only:
        convs = [c for c in convs if c.get("is_unread")]

    return {
        "total_found": len(convs),
        "conversations": convs[:limit]
    }

async def extract_conversation_thread(page, thread_id_or_index: str, limit: int = 20) -> Dict[str, Any]:
    """
    Lee el historial de mensajes de un hilo de conversación específico.
    """
    await human_delay(1.0, 2.0)
    
    # Si es una URL o thread_id directo
    if "/" in thread_id_or_index or len(thread_id_or_index) > 10:
        url = thread_id_or_index if thread_id_or_index.startswith("http") else f"https://www.linkedin.com/messaging/thread/{thread_id_or_index.strip('/')}/"
        await page.goto(url, wait_until="domcontentloaded")
    else:
        # Es un índice numérico o nombre: navegar a /messaging/ y hacer clic en el chat
        await page.goto("https://www.linkedin.com/messaging/", wait_until="domcontentloaded")
        await page.wait_for_selector("main", timeout=15000)
        try:
            idx = int(thread_id_or_index)
            clicked = await page.evaluate('''(targetIdx) => {
                const items = Array.from(document.querySelectorAll('main li.msg-conversation-listitem, main li[class*="msg-conversations"], main li'));
                const valid = items.filter(el => {
                    const txt = (el.innerText || '').trim();
                    return txt.length > 10 && !txt.startsWith('Estado:');
                });
                if (valid.length > targetIdx) {
                    const target = valid[targetIdx];
                    target.scrollIntoView({ behavior: 'instant', block: 'center' });
                    const clickTarget = target.querySelector('a, div, [role="button"]') || target;
                    clickTarget.click();
                    return true;
                }
                return false;
            }''', idx)
            if clicked:
                await asyncio.sleep(2)
        except ValueError:
            # Buscar por nombre del contacto
            clicked = await page.evaluate('''(name) => {
                const items = Array.from(document.querySelectorAll('main li'));
                const match = items.find(el => (el.innerText || '').toLowerCase().includes(name.toLowerCase()));
                if (match) {
                    match.scrollIntoView({ behavior: 'instant', block: 'center' });
                    const clickTarget = match.querySelector('a, div, [role="button"]') || match;
                    clickTarget.click();
                    return true;
                }
                return false;
            }''', thread_id_or_index)
            if clicked:
                await asyncio.sleep(2)

    await page.wait_for_selector('main', timeout=15000)
    await asyncio.sleep(2)

    thread_data = await page.evaluate('''() => {
        const messages = [];
        // Contenedores de mensajes en LinkedIn
        const msgItems = document.querySelectorAll(
            '[data-view-name="message-list-item"], .msg-s-message-list__event, .msg-s-event-listitem, [class*="message-item"]'
        );
        
        for (let item of Array.from(msgItems)) {
            const textEl = item.querySelector('.msg-s-event-listitem__body, [class*="message-body"], p');
            const text = textEl ? textEl.innerText.trim() : (item.innerText || '').trim();
            if (!text) continue;
            
            const senderEl = item.querySelector('.msg-s-message-group__name, [class*="sender"], [class*="actor__name"], h4, h3');
            const sender = senderEl ? senderEl.innerText.trim() : 'Participante';
            
            const timeEl = item.querySelector('time, [class*="time"], [class*="timestamp"]');
            const timeStr = timeEl ? timeEl.innerText.trim() : '';
            
            messages.push({
                sender,
                timestamp: timeStr,
                text
            });
        }
        
        // Extraer encabezado del chat (con quién se habla)
        const headerEl = document.querySelector('.msg-entity-lockup__entity-title, [class*="thread-title"], h2');
        const participantTitle = headerEl ? headerEl.innerText.trim() : '';

        return {
            participant: participantTitle,
            current_url: window.location.href,
            messages: messages
        };
    }''')

    msgs = thread_data.get("messages", [])
    if len(msgs) > limit:
        msgs = msgs[-limit:]

    return {
        "participant": thread_data.get("participant", ""),
        "thread_url": thread_data.get("current_url", page.url),
        "total_messages_loaded": len(msgs),
        "messages": msgs
    }

async def send_direct_message(page, recipient_or_thread: str, message_text: str) -> Dict[str, Any]:
    """
    Envía un mensaje directo en una conversación activa de LinkedIn.
    """
    await human_delay(1.0, 2.0)
    # Navegar al hilo si se proporcionó URL o ID
    if "/" in recipient_or_thread or len(recipient_or_thread) > 10:
        url = recipient_or_thread if recipient_or_thread.startswith("http") else f"https://www.linkedin.com/messaging/thread/{recipient_or_thread.strip('/')}/"
        await page.goto(url, wait_until="domcontentloaded")
    else:
        await page.goto("https://www.linkedin.com/messaging/", wait_until="domcontentloaded")
        await page.wait_for_selector("main", timeout=15000)
        await asyncio.sleep(2)
        matching = page.locator(f'main li:has-text("{recipient_or_thread}")').first
        if await matching.count() > 0:
            await matching.click()
            await asyncio.sleep(2)

    await page.wait_for_selector('main', timeout=15000)
    await asyncio.sleep(2)

    # Localizar editor de mensaje
    editor = page.locator('[role="textbox"][contenteditable="true"], .msg-form__contenteditable').first
    await editor.wait_for(state="visible", timeout=10000)
    await editor.click()
    await page.wait_for_timeout(300)
    await editor.fill(message_text)
    await page.wait_for_timeout(500)

    # Botón enviar
    send_btn = page.locator('button[type="submit"]:visible, button[data-control-name="send"]:visible, button:has-text("Enviar"):visible').first
    await send_btn.wait_for(state="visible", timeout=6000)
    await send_btn.click()
    await page.wait_for_timeout(2000)

    return {
        "status": "sent",
        "recipient_or_thread": recipient_or_thread,
        "message_preview": message_text[:120],
        "thread_url": page.url
    }

async def extract_profile_details(page, profile_url_or_username: str = "me") -> Dict[str, Any]:
    """
    Extrae la información completa y granular de un perfil de LinkedIn.
    Inspirado en eliasbiondo/linkedin-mcp-server con BeautifulSoup y parsing de SDUI.
    """
    await human_delay(1.5, 3.0)
    if profile_url_or_username.lower() in ["me", "self", ""]:
        url = "https://www.linkedin.com/in/me/"
    elif profile_url_or_username.startswith("http"):
        url = profile_url_or_username
    else:
        url = f"https://www.linkedin.com/in/{profile_url_or_username.strip('/')}/"

    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_selector("main", timeout=15000)
    await asyncio.sleep(2.5)

    # Scroll progresivo para hidratar las secciones lazy
    for _ in range(4):
        await page.mouse.wheel(0, 900)
        await asyncio.sleep(1.2)

    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")

    # 1. Cabecera principal
    h1 = soup.find("h1")
    name = h1.get_text(strip=True) if h1 else ""
    if not name:
        # Fallback al primer h2 en top-card
        for h2 in soup.find_all("h2"):
            t = h2.get_text(strip=True)
            if t and "notificaci" not in t.lower() and len(t) > 3:
                name = t
                break

    headline_el = soup.find("div", class_=lambda c: c and "text-body-medium" in c)
    headline = headline_el.get_text(strip=True) if headline_el else ""

    loc_el = soup.find("span", class_=lambda c: c and "text-body-small" in c and "t-black--light" in c)
    location = loc_el.get_text(strip=True) if loc_el else ""

    # 2. Secciones del perfil
    sections_data = {}
    for sec in soup.find_all("section"):
        header = sec.find(["h2", "h3"])
        if not header:
            continue
        title = header.get_text(strip=True)
        if not title or title.lower() in ["notificaciones", "idioma del perfil", "opciones de publicidad"]:
            continue

        sec_text = sec.get_text(separator="\n", strip=True)
        items = []
        for li in sec.find_all("li"):
            item_text = li.get_text(separator=" | ", strip=True)
            if len(item_text) > 10:
                items.append(item_text)

        title_lower = title.lower()
        if "acerca de" in title_lower or "about" in title_lower:
            sections_data["about"] = sec_text.replace(title, "").strip()
        elif "experiencia" in title_lower or "experience" in title_lower:
            sections_data["experience"] = items if items else [sec_text]
        elif "educaci" in title_lower or "education" in title_lower:
            sections_data["education"] = items if items else [sec_text]
        elif "destacado" in title_lower or "featured" in title_lower:
            sections_data["featured"] = items
        elif "conocimientos" in title_lower or "aptitudes" in title_lower or "skills" in title_lower:
            sections_data["skills"] = items
        elif "actividad" in title_lower or "activity" in title_lower:
            sections_data["activity"] = items
        else:
            sections_data[title] = items if items else sec_text[:300]

    return {
        "profile_url": page.url,
        "name": name,
        "headline": headline,
        "location": location,
        "about": sections_data.get("about", ""),
        "experience": sections_data.get("experience", []),
        "education": sections_data.get("education", []),
        "featured": sections_data.get("featured", []),
        "skills": sections_data.get("skills", []),
        "recent_activity": sections_data.get("activity", []),
        "all_sections": list(sections_data.keys())
    }

async def extract_feed_posts(page, limit: int = 10) -> Dict[str, Any]:
    """
    Extrae publicaciones del muro principal de LinkedIn (feed global).
    Inspirado en eliasbiondo/linkedin-mcp-server.
    """
    await human_delay(1.5, 2.5)
    await page.goto("https://www.linkedin.com/feed/", wait_until="commit", timeout=12000)
    await page.wait_for_selector("main", timeout=15000)
    await asyncio.sleep(2.5)

    # Scroll para disparar la carga progresiva de posts en el feed
    for _ in range(4):
        await page.mouse.wheel(0, 1000)
        await asyncio.sleep(1.2)

    posts_data = await page.evaluate('''() => {
        const results = [];
        // Estrategia semántica universal: encontrar botones de acción social de LinkedIn
        const buttons = Array.from(document.querySelectorAll('button'));
        const actionBtns = buttons.filter(b => {
            const t = (b.innerText || '').toLowerCase();
            const aria = (b.getAttribute('aria-label') || '').toLowerCase();
            return t.includes('recomendar') || t.includes('comentar') || aria.includes('recomendar') || aria.includes('like');
        });
        
        const seenContainers = new Set();
        for (let b of actionBtns) {
            let container = b.closest('div[class*="feed"], div[data-id], [role="article"], div[data-view-name*="feed"]') || b.parentElement?.parentElement?.parentElement?.parentElement;
            if (!container || seenContainers.has(container)) continue;
            seenContainers.add(container);
            
            const text = (container.innerText || '').trim();
            if (text.length < 50) continue;
            
            const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);
            const author = lines.length > 0 ? lines[0] : 'Autor en LinkedIn';
            const headline = lines.length > 1 ? lines[1] : '';
            const content = lines.slice(2, 7).join(' ').slice(0, 500);
            
            const reactEl = container.querySelector('[class*="reactions-count"], [class*="social-counts"], [class*="social-details"]');
            const reactions = reactEl ? reactEl.innerText.trim() : '';

            results.push({
                author,
                author_headline: headline.slice(0, 120),
                text: content,
                reactions,
                summary: text.slice(0, 180).replace(/\\n+/g, ' | ')
            });
            if (results.length >= 20) break;
        }
        return results;
    }''')

    return {
        "feed_url": page.url,
        "total_extracted": len(posts_data),
        "posts": posts_data[:limit]
    }

async def extract_job_details(page, job_url_or_id: str) -> Dict[str, Any]:
    """
    Extrae la descripción detallada de una oferta de empleo a partir de su ID o URL.
    """
    await human_delay(1.5, 2.5)
    if job_url_or_id.startswith("http"):
        url = job_url_or_id
    else:
        url = f"https://www.linkedin.com/jobs/view/{job_url_or_id.strip('/')}/"

    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_selector("main", timeout=15000)
    await asyncio.sleep(2.5)

    job_data = await page.evaluate('''() => {
        const titleEl = document.querySelector('h1, [class*="job-title"], .t-24');
        const title = titleEl ? titleEl.innerText.trim() : '';
        
        const companyEl = document.querySelector('[class*="company-name"], a[href*="/company/"]');
        const company = companyEl ? companyEl.innerText.trim() : '';
        const companyUrl = companyEl ? companyEl.getAttribute('href') : '';
        
        const locEl = document.querySelector('[class*="bullet"], [class*="location"], [class*="tertiary-description"]');
        const location = locEl ? locEl.innerText.trim() : '';
        
        // Descripción completa (expandir si hay botón)
        let moreBtn = document.querySelector('button[aria-label*="descripción"], button[aria-label*="description"]');
        if (!moreBtn) {
            const btns = Array.from(document.querySelectorAll('button'));
            moreBtn = btns.find(b => (b.innerText || '').includes('Ver más') || (b.innerText || '').includes('ver más') || (b.innerText || '').includes('See more'));
        }
        if (moreBtn) moreBtn.click();
        
        const descEl = document.querySelector('#job-details, [data-sdui-component*="aboutTheJob"], .jobs-description__content');
        const description = descEl ? descEl.innerText.trim() : '';

        // Badges (modalidad, tipo de jornada)
        const badges = Array.from(document.querySelectorAll('[class*="workplace-type"], [class*="job-insight"], span[class*="badge"]'))
            .map(b => b.innerText.trim())
            .filter(Boolean);

        return {
            title,
            company,
            company_url: companyUrl ? (companyUrl.startsWith('http') ? companyUrl : `https://www.linkedin.com${companyUrl}`) : '',
            location,
            badges: Array.from(new Set(badges)),
            description: description || document.querySelector('main')?.innerText.slice(0, 1500) || ''
        };
    }''')

    return {
        "job_url": page.url,
        **job_data
    }

async def extract_company_details(page, company_url_or_slug: str) -> Dict[str, Any]:
    """
    Extrae la información institucional completa de una página de empresa / organización.
    """
    await human_delay(1.5, 2.5)
    slug = company_url_or_slug.strip("/").split("/")[-1]
    url = f"https://www.linkedin.com/company/{slug}/about/"

    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_selector("main", timeout=15000)
    await asyncio.sleep(2.5)

    comp_data = await page.evaluate('''() => {
        const nameEl = document.querySelector('h1, [class*="org-top-card-summary__title"]');
        const name = nameEl ? nameEl.innerText.trim() : '';
        
        const overviewEl = document.querySelector('p[class*="break-words"], section[class*="about"] p');
        const overview = overviewEl ? overviewEl.innerText.trim() : '';
        
        const details = {};
        const dts = document.querySelectorAll('dl dt');
        for (let dt of Array.from(dts)) {
            const key = dt.innerText.trim().toLowerCase();
            const dd = dt.nextElementSibling;
            if (dd && dd.tagName === 'DD') {
                details[key] = dd.innerText.trim();
            }
        }

        return {
            name,
            overview,
            website: details['sitio web'] || details['website'] || '',
            industry: details['sector'] || details['industry'] || '',
            size: details['tamaño de la empresa'] || details['company size'] || '',
            headquarters: details['sede'] || details['headquarters'] || '',
            specialties: details['especialidades'] || details['specialties'] || ''
        };
    }''')

    return {
        "company_url": page.url,
        **comp_data
    }

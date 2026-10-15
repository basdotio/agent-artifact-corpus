"""JavaScript snippets run inside the page. Values are injected with json.dumps, never formatted raw."""

from __future__ import annotations

import json

REF_ATTR = "data-mcp-ref"

SNAPSHOT = "({title: document.title, url: location.href, ready: document.readyState})"

_INTERACTIVE = (
    "a[href],button,input,select,textarea,summary,[role=button],[role=link],[role=checkbox],"
    "[role=tab],[role=menuitem],[onclick],[contenteditable=true]"
)

_DESCRIBE = """
function describe(el, ref) {
  const r = el.getBoundingClientRect();
  const label = (el.innerText || el.value || el.getAttribute('aria-label') || el.placeholder ||
                 el.title || el.alt || el.name || '').toString().trim().replace(/\\s+/g, ' ').slice(0, 80);
  return {ref, tag: el.tagName.toLowerCase(), type: el.type || undefined, text: label,
          href: el.href || undefined, value: (el.type === 'password' ? undefined : el.value),
          checked: el.checked, disabled: el.disabled || undefined,
          rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]};
}
function visible(el) {
  const r = el.getBoundingClientRect(), s = getComputedStyle(el);
  return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
}
function refOf(el) {
  let ref = el.getAttribute('%(attr)s');
  if (!ref) { window.__mcpN = (window.__mcpN || 0) + 1; ref = 'e' + window.__mcpN; el.setAttribute('%(attr)s', ref); }
  return ref;
}
""" % {"attr": REF_ATTR}


def page_text(selector: str | None, limit: int) -> str:
    return (
        "(() => { const root = "
        + (f"document.querySelector({json.dumps(selector)})" if selector else "document.body")
        + "; if (!root) return null; return {title: document.title, url: location.href,"
        f" text: (root.innerText || '').slice(0, {int(limit)}), length: (root.innerText || '').length}}; }})()"
    )


def interactives(limit: int) -> str:
    return (
        "(() => {"
        + _DESCRIBE
        + f"const out = []; for (const el of document.querySelectorAll({json.dumps(_INTERACTIVE)}))"
        f" {{ if (!visible(el)) continue; out.push(describe(el, refOf(el))); if (out.length >= {int(limit)}) break; }}"
        " return out; })()"
    )


def find(query: str, limit: int) -> str:
    return (
        "(() => {" + _DESCRIBE + f"const q = {json.dumps(query.lower())}; const out = [];"
        " const cands = document.querySelectorAll('a,button,input,select,textarea,label,summary,h1,h2,h3,h4,li,td,th,p,span,div,[role]');"
        " for (const el of cands) { if (!visible(el)) continue;"
        " const hay = [el.innerText, el.value, el.getAttribute('aria-label'), el.placeholder, el.title, el.alt, el.name, el.id]"
        "   .filter(Boolean).join(' ').toLowerCase();"
        f" if (hay.includes(q) && (el.children.length < 4 || el.matches('a,button,input,select,textarea,label')))"
        f" {{ out.push(describe(el, refOf(el))); if (out.length >= {int(limit)}) break; }} }}"
        " return out; })()"
    )


def tables(selector: str | None, limit: int) -> str:
    scope = f"document.querySelector({json.dumps(selector)})" if selector else "document"
    return (
        "(() => { const scope = " + scope + "; if (!scope) return null; const out = [];"
        f" for (const t of scope.querySelectorAll('table')) {{ if (out.length >= {int(limit)}) break;"
        " const rows = Array.from(t.querySelectorAll('tr')).map(tr => Array.from(tr.children).map(c => c.innerText.trim()));"
        " if (!rows.length) continue; const head = t.querySelector('thead tr, tr');"
        " const headers = Array.from(head.children).map(c => c.innerText.trim());"
        " const body = rows.slice(1).map(r => Object.fromEntries(headers.map((h, i) => [h || ('col' + (i + 1)), r[i] ?? ''])));"
        " out.push({headers, rows: body}); } return out; })()"
    )


def links(selector: str | None, limit: int) -> str:
    scope = f"document.querySelector({json.dumps(selector)})" if selector else "document"
    return (
        "(() => { const scope = " + scope + "; if (!scope) return null;"
        f" return Array.from(scope.querySelectorAll('a[href]')).slice(0, {int(limit)})"
        ".map(a => ({text: (a.innerText || a.title || '').trim().slice(0, 80), href: a.href})); })()"
    )


def _target(ref: str | None, selector: str | None) -> str:
    if ref:
        return f"document.querySelector('[{REF_ATTR}=' + JSON.stringify({json.dumps(ref)}) + ']')"
    return f"document.querySelector({json.dumps(selector)})"


def act(
    action: str,
    ref: str | None,
    selector: str | None,
    value: str | None = None,
    clear: bool = False,
) -> str:
    """One page-side action on an element; returns {ok, ...} or {error}."""
    body = {
        "click": "el.scrollIntoView({block:'center'}); el.click(); return {ok:true};",
        "focus": "el.scrollIntoView({block:'center'}); el.focus(); return {ok:true};",
        "hover": "el.dispatchEvent(new MouseEvent('mouseover', {bubbles:true})); return {ok:true};",
        "scroll_into_view": "el.scrollIntoView({block:'center'}); return {ok:true};",
        "submit": (
            "const form = el.form || el.closest('form');"
            " if (form) { form.requestSubmit ? form.requestSubmit() : form.submit(); return {ok:true, via:'form'}; }"
            " el.click(); return {ok:true, via:'click'};"
        ),
        "select": (
            f"const v = {json.dumps(value)}; const opt = Array.from(el.options || []).find(o => o.value === v || o.text === v);"
            " if (!opt) return {error: 'no such option'}; el.value = opt.value;"
            " el.dispatchEvent(new Event('input', {bubbles:true})); el.dispatchEvent(new Event('change', {bubbles:true}));"
            " return {ok:true, value: el.value};"
        ),
        "check": (
            f"const want = {json.dumps(value not in ('false', '0'))}; if (el.checked !== want) el.click(); return {{ok:true, checked: el.checked}};"
        ),
        "prepare_type": (
            "el.scrollIntoView({block:'center'}); el.focus();"
            + (
                " if ('value' in el) { el.select && el.select(); el.value = ''; el.dispatchEvent(new Event('input', {bubbles:true})); }"
                if clear
                else ""
            )
            + " return {ok:true, tag: el.tagName.toLowerCase(), type: el.type || '', name: el.name || el.id || '',"
            " hint: [el.placeholder, el.getAttribute('aria-label'), el.autocomplete, el.name, el.id].filter(Boolean).join(' ')};"
        ),
    }[action]
    return (
        "(() => { const el = "
        + _target(ref, selector)
        + "; if (!el) return {error: 'element not found'};"
        " try { " + body + " } catch (e) { return {error: String(e)}; } })()"
    )


def wait_condition(text: str | None, selector: str | None, url_contains: str | None) -> str:
    return (
        "(() => { const ok = document.readyState !== 'loading'"
        + (
            f" && (document.body && document.body.innerText.toLowerCase().includes({json.dumps((text or '').lower())}))"
            if text
            else ""
        )
        + (f" && !!document.querySelector({json.dumps(selector)})" if selector else "")
        + (f" && location.href.includes({json.dumps(url_contains)})" if url_contains else "")
        + "; return ok; })()"
    )


def file_input(ref: str | None, selector: str | None) -> str:
    return _target(ref, selector)


def items(limit: int) -> str:
    """Repeated items (search results, cards, listings): the largest group of same-shaped
    siblings that carry text. Returns {total, items: [{text, link}]}."""
    return (
        "(() => { let best = null, bestScore = 0;"
        " for (const parent of document.querySelectorAll('body *')) {"
        "  const kids = Array.from(parent.children); if (kids.length < 3) continue;"
        "  const groups = {};"
        "  for (const k of kids) { const t = (k.innerText || '').trim(); if (t.length < 3) continue;"
        "   const key = k.tagName + '.' + (k.className && k.className.baseVal === undefined ? k.className : '');"
        "   (groups[key] = groups[key] || []).push(k); }"
        "  for (const g of Object.values(groups)) { if (g.length < 3) continue;"
        "   const score = g.length * Math.min(200, g.reduce((n, k) => n + (k.innerText || '').length, 0) / g.length);"
        "   if (score > bestScore) { bestScore = score; best = g; } } }"
        " if (!best) return {total: 0, items: []};"
        " const rows = best.map(k => { const a = k.matches('a[href]') ? k : k.querySelector('a[href]');"
        "  return {text: (k.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 300), link: a ? a.href : null}; });"
        f" return {{total: rows.length, items: rows.slice(0, {int(limit)})}}; }})()"
    )

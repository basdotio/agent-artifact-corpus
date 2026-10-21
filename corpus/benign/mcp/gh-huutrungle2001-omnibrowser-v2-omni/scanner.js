({tabId}) => {
  // State is document-local, not tied to a driver or a Python process.
  const key = '__omni_v1_document__';
  let state = window[key];
  if (!state || state.document !== document || state.tabId !== tabId || !state.live) {
    // getRandomValues is available on ordinary HTTP as well as secure origins.
    const id = Array.from(crypto.getRandomValues(new Uint8Array(16)),
      byte => byte.toString(16).padStart(2, '0')).join('');
    state = {document, tabId, live: true, id, next: 0,
             nodes: new Map(), refs: new WeakMap(), roots: new WeakSet()};
    const removed = node => {
      const oldRef = state.refs.get(node);
      if (oldRef) {
        state.nodes.get(oldRef).detached = true;
        state.refs.delete(node);
      }
      for (const child of node.childNodes) removed(child);
      if (node.shadowRoot) removed(node.shadowRoot);
    };
    state.observer = new MutationObserver(records => {
      for (const record of records) for (const node of record.removedNodes) removed(node);
    });
    Object.defineProperty(window, key, {value: state, configurable: true});
    // BFCache restoration is a new visit; old refs must not come back to life.
    addEventListener('pagehide', () => { state.live = false; }, {once: true});
  }
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const parent = el => el.parentElement || el.getRootNode().host;
  const visible = (el, requireBox = true) => {
    if (requireBox && !el.getClientRects().length) return false;
    for (let p = el; p; p = parent(p)) {
      const s = getComputedStyle(p);
      if (p.hidden || p.inert || s.display === 'none' || s.visibility === 'hidden' ||
          s.visibility === 'collapse' || s.contentVisibility === 'hidden') return false;
    }
    return true;
  };
  const identity = el => JSON.stringify([el.localName, el.getAttribute('role'),
    el.getAttribute('type'), el.getAttribute('href'), el.href?.baseVal || el.href,
    el.id, el.getAttribute('name'), el.getAttribute('formaction'), el.form?.action]);
  // Act uses this exact predicate too; refs are never rebound by text/selector.
  state.identity = identity;
  const ref = el => {
    let value = state.refs.get(el);
    if (!value || state.nodes.get(value).identity !== identity(el)) {
      value = `${state.id}.n${++state.next}`;
      state.refs.set(el, value);
      state.nodes.set(value, {node: el, identity: identity(el)});
    }
    return value;
  };
  const text = el => {
    if (el.matches('input,textarea,select,[contenteditable]:not([contenteditable="false"])')) return '';
    let result = '';
    for (const child of el.childNodes) {
      if (child.nodeType === Node.TEXT_NODE) result += child.textContent;
      else if (child.nodeType === Node.ELEMENT_NODE &&
               !child.matches('script,style,noscript,template') && visible(child, false)) result += ' ' + text(child);
    }
    return norm(result);
  };
  const name = el => {
    const ids = (el.getAttribute('aria-labelledby') || '').split(/\s+/).filter(Boolean);
    const labelled = norm(ids.map(id => {
      const target = el.getRootNode().getElementById?.(id);
      return target ? text(target) : '';
    }).join(' '));
    return labelled || norm(el.getAttribute('aria-label')) ||
      norm(Array.from(el.labels || []).map(text).join(' ')) ||
      norm(el.getAttribute('placeholder')) || text(el) || norm(el.getAttribute('title')) ||
      (el.matches('input[type=submit]') ? 'Submit' : el.matches('input[type=reset]') ? 'Reset' : '');
  };
  const roles = new Set(['button', 'textbox', 'searchbox', 'checkbox', 'radio', 'combobox',
    'listbox', 'option', 'switch', 'slider', 'spinbutton', 'tab', 'menuitem',
    'menuitemcheckbox', 'menuitemradio', 'treeitem']);
  const elements = [];
  const collect = root => {
    if (!state.roots.has(root) && (root === document || root instanceof ShadowRoot)) {
      state.observer.observe(root, {subtree: true, childList: true});
      state.roots.add(root);
    }
    for (const el of root.children) {
      elements.push(el);
      collect(el);
      if (el.shadowRoot) collect(el.shadowRoot);
    }
  };
  collect(document);
  const links = [], controls = [];
  let frames = 0;
  for (const el of elements) {
    if (el.matches('iframe,frame')) frames++;
    if (!visible(el)) continue;
    const role = el.getAttribute('role');
    if (el.matches('a[href],area[href]') || role === 'link') {
      let href = null;
      try { href = el.hasAttribute('href') ? new URL(el.getAttribute('href'), el.baseURI).href : null; } catch {}
      links.push({ref: ref(el), text: name(el), href,
        download_hint: el.hasAttribute('download') || /\.(pdf|zip|docx?|xlsx?|pptx?|csv|epub)(?:[?#]|$)/i.test(href || '')});
      continue;
    }
    if (!el.matches('button,input:not([type=hidden]),textarea,select') &&
        !(el.isContentEditable && !parent(el)?.isContentEditable) && !roles.has(role)) continue;
    const type = el.getAttribute('type') || (el.matches('input') ? 'text' : null);
    const nativeRole = el.matches('button,input[type=button],input[type=submit],input[type=reset]') ? 'button' :
      el.matches('select') ? 'combobox' : el.matches('input[type=checkbox]') ? 'checkbox' :
      el.matches('input[type=radio]') ? 'radio' : el.matches('input[type=range]') ? 'slider' : 'textbox';
    let disabled = el.matches(':disabled');
    for (let ancestor = el; ancestor; ancestor = parent(ancestor)) {
      if (ancestor.getAttribute('aria-disabled') === 'true') disabled = true;
    }
    const item = {ref: ref(el), role: role || nativeRole, name: name(el), disabled};
    if (type !== null) item.type = type;
    controls.push(item);
  }
  const candidates = elements.filter(el => visible(el) && el.matches('main,[role=main],article'));
  const largestRegion = candidates.length ? null : elements
    .filter(el => el.matches('section,div') && visible(el, false) &&
      !el.closest('nav,header,footer,aside,dialog,[role=dialog],[role=alertdialog]'))
    .map(el => ({el, length: text(el).length})).filter(item => item.length >= 200)
    .sort((a,b) => b.length - a.length)[0]?.el;
  const region = candidates.find(el => el.matches('main,[role=main]')) ||
    candidates.sort((a,b) => text(b).length - text(a).length)[0] || largestRegion || document.body;
  const blocks = new Set(['H1','H2','H3','H4','H5','H6','P','LI','TR','DIV','SECTION','ARTICLE',
                          'MAIN','HEADER','FOOTER','UL','OL','TABLE','PRE','BLOCKQUOTE','BR']);
  const chunks = [];
  const extract = el => {
    if (!el || !visible(el, false) || el.matches('script,style,noscript,template,input,textarea,select,[contenteditable]:not([contenteditable="false"])')) return;
    if (region === document.body && el !== region && el.matches('nav,header,footer,aside') &&
        !el.closest('dialog,[role=dialog],[role=alertdialog]')) return;
    if (blocks.has(el.tagName)) chunks.push('\n');
    for (const child of el.childNodes) {
      if (child.nodeType === Node.TEXT_NODE) chunks.push(child.textContent);
      else if (child.nodeType === Node.ELEMENT_NODE) extract(child);
    }
    if (el.shadowRoot) for (const child of el.shadowRoot.children) extract(child);
    if (blocks.has(el.tagName)) chunks.push('\n');
    else if (el.matches('td,th')) chunks.push('\t');
  };
  extract(region);
  // Dialogs outside main are still content, not disposable site chrome.
  for (const el of elements.filter(el => el.matches('dialog,[role=dialog],[role=alertdialog]'))) {
    if (!region?.contains(el)) extract(el);
  }
  return {tab_id: tabId, url: location.href, title: document.title,
    content: chunks.join('').split(/\n+/).map(norm).filter(Boolean).join('\n'), links, controls,
    truncated: false, coverage: {content_truncated: false, links_omitted: 0,
                                controls_omitted: 0, unsupported_frames: frames}};
}

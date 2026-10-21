// Exact backend-node bridge only: extraction belongs to the vendored reader.
({tabId}) => {
  const key = '__omni_v1_document__';
  let state = window[key];
  if (!state || state.bridge !== 2 || state.document !== document ||
      state.tabId !== tabId || !state.live) {
    if (state) { state.live = false; state.observer?.disconnect(); }
    const id = Array.from(crypto.getRandomValues(new Uint8Array(16)),
      byte => byte.toString(16).padStart(2, '0')).join('');
    state = {bridge: 2, document, tabId, live: true, id, next: 0,
      nodes: new Map(), refs: new WeakMap(), roots: new WeakSet()};
    state.identity = el => JSON.stringify([el.localName, el.getAttribute('role'),
      el.getAttribute('type'), el.getAttribute('href'), el.href?.baseVal || el.href,
      el.id, el.getAttribute('name'), el.getAttribute('formaction'), el.form?.action,
      el.getAttribute('contenteditable')]);
    state.drop = ref => {
      const entry = state.nodes.get(ref);
      if (entry) { state.refs.delete(entry.node); state.nodes.delete(ref); }
    };
    state.prune = () => {
      for (const [ref, entry] of state.nodes) {
        if (!entry.node.isConnected || entry.node.ownerDocument !== document ||
            state.identity(entry.node) !== entry.identity) state.drop(ref);
      }
    };
    state.observer = new MutationObserver(records => {
      // Only walk tracked refs (<=512), not a potentially enormous removed tree.
      const removed = records.flatMap(record => Array.from(record.removedNodes));
      for (const [ref, entry] of state.nodes) {
        let detached = false;
        for (let p = entry.node; p; p = p.parentNode || p.host) {
          if (removed.includes(p)) { detached = true; break; }
        }
        if (detached) state.drop(ref);
      }
      state.prune();
    });
    state.watch = root => {
      if (!state.roots.has(root)) {
        state.observer.observe(root, {subtree: true, childList: true, attributes: true,
          attributeFilter: ['href', 'role', 'type', 'id', 'name', 'formaction', 'action', 'contenteditable']});
        state.roots.add(root);
      }
    };
    state.watch(document);
    state.bind = (node, expected, backendId, docId, baseURI) => {
      if (!state.live || state.id !== docId || state.document !== document ||
          !node || node.nodeType !== 1 || !node.isConnected || node.ownerDocument !== document ||
          node.baseURI !== baseURI) return null;
      // Never traverse an iframe or closed root, even if CDP can resolve it.
      for (let root = node.getRootNode(); root !== document; root = root.host?.getRootNode()) {
        if (!(root instanceof ShadowRoot) || root.mode !== 'open') return null;
        state.watch(root);
      }
      for (const [name, value] of Object.entries(expected)) {
        if ((name === '_tag' ? node.localName : node.getAttribute(name)) !== value) return null;
      }
      const identity = state.identity(node);
      let ref = state.refs.get(node);
      if (!ref || !state.nodes.has(ref)) {
        while (state.nodes.size >= 512) state.drop(state.nodes.keys().next().value);
        ref = `${state.id}.n${++state.next}`;
        state.nodes.set(ref, {node, identity, backendId});
        state.refs.set(node, ref);
      }
      return ref;
    };
    Object.defineProperty(window, key, {value: state, configurable: true});
    addEventListener('pagehide', () => {
      state.live = false; state.observer.disconnect(); state.nodes.clear();
    }, {once: true});
  }
  state.prune();
  // A per-document signing key never appears in observation/cursor output.
  state.cursorKey ||= Array.from(crypto.getRandomValues(new Uint8Array(32)),
    byte => byte.toString(16).padStart(2, '0')).join('');
  return {id: state.id, url: location.href, title: document.title,
    baseURI: document.baseURI, cursor_key: state.cursorKey};
}

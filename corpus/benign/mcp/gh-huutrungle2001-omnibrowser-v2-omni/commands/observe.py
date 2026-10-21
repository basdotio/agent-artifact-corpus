from importlib.resources import files
import json
import time

from ..pagination import paginate
from ..errors import OmniError


def observe(page, tab_id, max_bytes, pretty=False, timeout=10000, cursor=None):
    from playwright.sync_api import Error
    from .._vendor.browser_use_dom.enhanced_snapshot import REQUIRED_COMPUTED_STYLES
    from ..reader import render_observation
    from ..errors import stale

    script = files("omni").joinpath("refs.js").read_text(encoding="utf-8")
    deadline = time.monotonic() + timeout / 1000
    session = page.context.new_cdp_session(page)
    group = "omni-reader"

    def remaining():
        ms = int((deadline - time.monotonic()) * 1000)
        if ms <= 0:
            raise OmniError("TIMEOUT", "Observation timed out; observe again.", 5)
        return ms

    def send(method, params=None):
        remaining()
        return session.send(method, params or {})

    def value(response):
        if response.get("exceptionDetails"):
            raise OmniError("UNAVAILABLE_TARGET", "Reader bridge failed; observe again.", 4)
        return response.get("result", {}).get("value")

    try:
        metadata = value(send("Runtime.evaluate", {
            "expression": f"({script})({json.dumps({'tabId': tab_id})})",
            "returnByValue": True, "timeout": remaining(),
        }))
        dom = send("DOM.getDocument", {"depth": -1, "pierce": True})["root"]
        ax = send("Accessibility.getFullAXTree")
        snapshot = send("DOMSnapshot.captureSnapshot", {
            "computedStyles": REQUIRED_COMPUTED_STYLES,
            "includePaintOrder": True, "includeDOMRects": True,
        })
        # Ignore all iframe documents, including same-origin frames returned by CDP.
        snapshot['documents'] = [d for d in snapshot['documents']
                                 if dom['backendNodeId'] in d['nodes'].get('backendNodeId', [])]
        if not snapshot['documents']:
            raise stale()
        result, candidates = render_observation(dom, ax, snapshot, metadata, tab_id)
        result, candidates = paginate(result, candidates, metadata, tab_id, max_bytes, pretty, cursor)
        resolved = []
        for backend_id, expected, kind, item in candidates:
            # Exact CDP identity, never an Nth element, text match or selector.
            # At most 96 selected refs: no per-node calls over the full DOM tree.
            try:
                remote = send("DOM.resolveNode", {"backendNodeId": backend_id, "objectGroup": group})['object']
                resolved.append({'objectId': remote['objectId']})
            except Error:
                # Removed nodes are omissions, not guessed targets. A disconnect is
                # caught by the final document check below, without action replay.
                resolved.append({'value': None})
        # All bindings share one page invocation; individual resolveNode calls are
        # necessary for real backend identities, and are capped independently of DOM size.
        window = send("Runtime.evaluate", {"expression": "window", "objectGroup": group})['result']['objectId']
        refs = value(send("Runtime.callFunctionOn", {
            "objectId": window,
            "functionDeclaration": """function(meta, entries, ...nodes) {
              const s = window.__omni_v1_document__;
              if (!s?.live || s.tabId !== meta.tabId || s.id !== meta.id) return [];
              s.prune();
              return nodes.map((node, i) => s.bind(node, entries[i][1], entries[i][0], meta.id, meta.baseURI));
            }""",
            "arguments": [{"value": {**metadata, 'tabId': tab_id}},
                          {"value": [[c[0], c[1]] for c in candidates]}, *resolved],
            "returnByValue": True,
        }))
        if refs is None or len(refs) != len(candidates):
            raise stale()
        bound = {'links': [], 'controls': []}
        for (_, _, kind, item), ref in zip(candidates, refs):
            if ref is None:
                result['coverage'][kind + '_omitted'] += 1
                result['coverage']['ref_bindings_failed'] += 1
                result['truncated'] = True
            else:
                bound[kind].append({'ref': ref, **item})
        result.update(bound)
        valid = value(send("Runtime.evaluate", {
            "expression": "(() => { const s = window.__omni_v1_document__; return !!s?.live && s.document === document && s.id === " + json.dumps(metadata['id']) + " && location.href === " + json.dumps(metadata['url']) + "; })()",
            "returnByValue": True, "timeout": remaining(),
        }))
        if not valid:
            raise stale()
    except Error as exc:
        if "timed out" in str(exc).lower() or "terminated" in str(exc).lower():
            raise OmniError("TIMEOUT", "Observation timed out; observe again.", 5) from None
        raise OmniError("UNAVAILABLE_TARGET", "Observation failed; inspect the tab.", 4) from None
    finally:
        try:
            session.send("Runtime.releaseObjectGroup", {"objectGroup": group})
            session.detach()
        except Error:
            pass
    return result

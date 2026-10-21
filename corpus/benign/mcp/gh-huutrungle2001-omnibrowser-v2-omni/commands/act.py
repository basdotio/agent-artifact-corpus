from ..errors import OmniError, stale


RESOLVE = """({ref, tabId}) => {
  const state = window.__omni_v1_document__;
  const entry = state?.nodes.get(ref);
  if (!state?.live || state.document !== document || state.tabId !== tabId || !entry ||
      entry.detached || !entry.node.isConnected || entry.node.ownerDocument !== document ||
      state.identity(entry.node) !== entry.identity) return null;
  return entry.node;
}"""


def act(page, tab_id, ref, action, value=None, timeout=10000, key=None, label=None):
    from playwright.sync_api import Error, TimeoutError
    handle = None
    try:
        handle = page.evaluate_handle(RESOLVE, {"ref": ref, "tabId": tab_id})
        element = handle.as_element()
        if element is None:
            raise stale()
        if not element.is_visible() or not element.is_enabled():
            raise OmniError("INVALID_ACTION", "Target is hidden or disabled; inspect the page.", 4)
        if action == "click":
            element.click(timeout=timeout, no_wait_after=True)
        elif action == "fill":
            allowed = element.evaluate("""el => el.isContentEditable || el.matches('textarea,input:not([type]),input[type=text],input[type=search],input[type=email],input[type=url],input[type=tel],input[type=password],input[type=number]')""")
            if not allowed:
                raise OmniError("INVALID_ACTION", "Target is not a text-like editable field.", 2)
            element.fill(value, timeout=timeout)
        elif action == "press":
            element.press(key, timeout=timeout)
        elif action == "select":
            if not element.evaluate("el => el instanceof HTMLSelectElement"):
                raise OmniError("UNSUPPORTED_ACTION", "Select requires a native HTML select element.", 2)
            if value is not None:
                element.select_option(value=value, timeout=timeout)
            else:
                element.select_option(label=label, timeout=timeout)
        else:
            raise OmniError("INVALID_ACTION", "Unsupported action.", 2)
        return {"ok": True, "tab_id": tab_id, "ref": ref, "action": action, "url": page.url}
    except TimeoutError:
        raise OmniError("TIMEOUT", "Action timed out; inspect before retrying. It was not replayed.", 5) from None
    except Error:
        # Never include Playwright messages: fill call logs can contain the secret value.
        try:
            valid = page.evaluate(RESOLVE, {"ref": ref, "tabId": tab_id}) is not None
        except Error:
            valid = False
        if not valid:
            raise stale() from None
        raise OmniError("INVALID_ACTION", "Action failed; inspect before retrying. It was not replayed.", 4) from None
    finally:
        if handle:
            handle.dispose()

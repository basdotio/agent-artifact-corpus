"""One native wheel input targeted at the main scrolling document only."""
from ..errors import OmniError

METRICS = """() => {
  const el = document.scrollingElement;
  return {x: scrollX, y: scrollY, document_width: el?.scrollWidth || 0,
    document_height: el?.scrollHeight || 0, viewport_width: innerWidth, viewport_height: innerHeight};
}"""
POINT = """() => {
  // Pick a hit-tested location whose composed ancestry has no inner scroller.
  for (const [fx, fy] of [[.5,.5],[.02,.5],[.98,.5],[.5,.1],[.5,.9]]) {
    const x = Math.max(1, Math.min(innerWidth - 2, innerWidth * fx));
    const y = Math.max(1, Math.min(innerHeight - 2, innerHeight * fy));
    let el = document.elementFromPoint(x, y), safe = true;
    while (el?.shadowRoot?.elementFromPoint(x,y)) {
      const inner = el.shadowRoot.elementFromPoint(x,y);
      if (inner === el) break;
      el = inner;
    }
    for (let p = el; p; p = p.parentElement || p.getRootNode()?.host) {
      if (['IFRAME','FRAME'].includes(p.tagName)) { safe = false; break; }
      if (p === document.scrollingElement || p === document.body || p === document.documentElement) continue;
      const s = getComputedStyle(p);
      if (/(auto|scroll|overlay)/.test(s.overflowY) && p.scrollHeight > p.clientHeight) { safe = false; break; }
    }
    if (safe && el) return {x,y};
  }
  return null;
}"""


def scroll(page, tab_id, direction='down', amount=None, timeout=10000):
    from playwright.sync_api import Error, TimeoutError
    try:
        before = page.evaluate(METRICS)
        point = page.evaluate(POINT)
        if point is None:
            raise OmniError('UNSUPPORTED_SCROLL', 'No unobstructed main-document wheel target; inner panes/iframes are unsupported.', 2)
        amount = amount if amount is not None else max(100, min(800, int(before['viewport_height'] * .75)))
        page.mouse.move(point['x'], point['y'])
        page.mouse.wheel(0, amount if direction == 'down' else -amount)
        try:
            page.wait_for_function('old => scrollX !== old.x || scrollY !== old.y', arg=before, timeout=min(timeout, 750))
        except TimeoutError:
            pass  # At a boundary/preventDefault: report actual lack of movement.
        after = page.evaluate(METRICS)
        return {'ok': True, 'tab_id': tab_id, 'direction': direction, 'amount': amount,
                'unit': 'css_pixels', 'target': 'document', 'before': before, 'after': after,
                'moved': before['x'] != after['x'] or before['y'] != after['y'],
                'at_current_bottom': after['y'] + after['viewport_height'] >= after['document_height'] - 1}
    except Error:
        raise OmniError('SCROLL', 'Wheel operation failed; inspect before retrying. It was not replayed.', 4) from None

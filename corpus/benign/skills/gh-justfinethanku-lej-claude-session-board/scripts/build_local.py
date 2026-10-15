#!/usr/bin/env python3
"""Turn the board fragment into a standalone page you open from disk.

    python3 scripts/build_local.py <board.html> <out.html>

<board.html> is the filled template (the same fragment the Artifact tool publishes). The output adds the
doctype, charset and viewport, plus a script that reloads the page every 60 seconds so the open tab picks up
each rewrite. It won't reload while you're typing or within 20 seconds of your last click, and it keeps your
scroll position. Edited replies and "Copied" marks survive, since the page keeps them in localStorage.
"""
import sys

RELOAD = """<script id="local-autoreload">
(function () {
  var last = Date.now();
  ['keydown', 'input', 'mousedown', 'scroll'].forEach(function (e) {
    document.addEventListener(e, function () { last = Date.now(); }, true);
  });
  var y = 0;
  try { y = +sessionStorage.getItem('board-scroll') || 0; } catch (e) {}
  if (y) window.addEventListener('load', function () { window.scrollTo(0, y); });
  setInterval(function () {
    var a = document.activeElement;
    var typing = a && (a.tagName === 'TEXTAREA' || a.tagName === 'INPUT' || a.isContentEditable);
    if (typing || Date.now() - last < 20000) return;
    try { sessionStorage.setItem('board-scroll', String(window.scrollY)); } catch (e) {}
    location.reload();
  }, 60000);
})();
</script>"""


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    body = open(src, encoding="utf-8").read()
    page = (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n</head>\n<body>\n'
        + body + "\n" + RELOAD + "\n</body>\n</html>\n"
    )
    with open(dst, "w", encoding="utf-8") as f:
        f.write(page)
    print("wrote", dst)


if __name__ == "__main__":
    main()

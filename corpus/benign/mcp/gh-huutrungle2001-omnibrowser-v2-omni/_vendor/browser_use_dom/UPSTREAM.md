# browser-use reader subset

- Repository: https://github.com/browser-use/browser-use
- Verified source commit: `aa093a843da5edbf323c0b4145c9b6a0db3ecde8`
- Vendored on: 2026-10-19. MIT; complete upstream LICENSE included.
- Copyright (c) 2024 Gregor Zunic.

Copied/adapted source:

| Local file | Upstream source and retained logic |
| --- | --- |
| `enhanced_snapshot.py` | `browser_use/dom/enhanced_snapshot.py`: REQUIRED_COMPUTED_STYLES, rare boolean/style parsing, build_snapshot_lookup's indexed layout/backend-ID join |
| `clickable_elements.py` | `browser_use/dom/serializer/clickable_elements.py`: ClickableElementDetector, including bounded depth-two form descendants, AX states/roles, attributes, search/icon/cursor heuristics |
| `paint_order.py` | `browser_use/dom/serializer/paint_order.py`: Rect, RectUnionPure, PaintOrderRemover (paint groups, occlusion, background/opacity handling) |
| `visibility.py` | `browser_use/dom/service.py`: CSS/bounds portion of is_element_visible_according_to_all_parents |
| `markdown_extractor.py` | `browser_use/dom/markdown_extractor.py`: convert_html_to_markdown and _preprocess_markdown_content only |
| `views.py` | Minimal replacement compatible models based on `browser_use/dom/views.py`; no serialization framework |

Local changes: imports target these slim models instead of browser_use/cdp_use;
all snapshot field-value extraction, logging and framework dependencies removed.
Snapshot bounds remain in CDP CSS-pixel coordinates (no DPR division). The
clickable detector excludes iframe/frame and reports disabled controls as
interactive so Omni can return their state without activating them. Visibility
adds collapsed/zero-area rejection, omits iframe transforms and retains offscreen
content. PaintOrderRemover's algorithm is retained; Omni supplies a flat bounded
list of visible nodes (max 3000) instead of a recursive framework tree. No event
listener probing per DOM node: the adapter uses batch snapshot isClickable.

`omni/reader.py`, `omni/observe.py` and `omni/refs.js` are local glue, not upstream
source: main/open-shadow filtering, sanitized HTML -> upstream markdown conversion,
bounded compact output, and exact backend-ID -> resolved-node -> document Map.
The node cap is 50000, content HTML cap 1000000 characters, ref binding cap 96 per
response and retained map cap 512. Candidate discovery is no longer globally
capped at 96: local `pagination.py` continues all three streams by signed cursor.
Omni command implementations now live under `omni/commands/`; vendor code and
MIT notices remain intact. Omissions/limited processing are reported.
Native actions/download code is Omni's existing implementation, not vendored.

Runtime additions: markdownify for the copied conversion functions; the standard
MCP Python SDK is used separately for transport. No browser-use framework, LLM,
telemetry, cloud, broker, agent loop, Python exec or browser-harness daemon.

This is an adapted subset, not a claim of upstream API compatibility or equivalent
extraction quality. Runtime/browser behavior has not been exercised for this
initial revision. The later command/pagination revision was directly exercised
on a harmless local demo through actual Omni CLI/MCP. No upstream
source or legacy browser package was changed.

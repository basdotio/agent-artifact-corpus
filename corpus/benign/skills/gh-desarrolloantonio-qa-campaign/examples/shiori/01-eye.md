# 01 — EYE pass

Build `f993848` (1.52.02-staging) · account A · `emu` phone 411×914 dp, tablet 1280×800 dp (`ui.py size`), demo mode on · light / dark (app Theme setting, put back to Auto) · compact view (turned on for the shot, then off again). Screenshots in `qa-shots/01/`, **every one opened**. No fixtures created, nothing written to the server; one tag rename and one tag delete dialog were opened and cancelled (`test2`, not ours).

## Inventory — screens and what was seen (R5 EYE)

| Screen | Shot | Seen |
|---|---|---|
| Feed, full cards | `p-feed` | fine: image, title, date, tag chips, 5 actions, FAB clear of content |
| Tag filter sheet | `p-filter`, `d-filter` | **3 tags that don't exist on the server** (T-02); title "Categories" (EYE-07) |
| Settings top / Data+Debug / bottom | `p-settings`, `p-settings2`, `p-settings3` | fine; Debug section is staging-only (`SettingsScreen.kt:283`); still no username (ABS-03, known) |
| Manage tags · row menu · Rename · Delete · New tag | `p-tags`, `p-tagmenu`, `p-rename`, `p-tagdelete`, `p-newtag` | fine; delete names the tag and says how many bookmarks use it |
| Last crash log (staging) | `p-crash` | fine, empty state centred |
| Network logs (staging) | `p-netlog` | opens scrolled mid-list, first entry cut under the bar; staging-only → not rated |
| Reader, top and end | `p-reader`, `p-reader-end`, `d-reader` | broken inline image (EYE-02); body text ~9 dp from the edges while the header has 16 (EYE-01) |
| Edit | `p-edit` | fine (URL not editable, ABS-12 known) |
| Add manually | `p-add`, `d-add` | fine; the disabled "Add bookmark" is still readable |
| Delete bookmark dialog | `p-delete` | doesn't name the bookmark and doesn't say it's permanent (EYE-07) |
| Update cache dialog | `p-update` | the whole question set as a headline; Cancel as heavy as Update (EYE-03) |
| Selection mode | `p-select` | outline + tint on the selected card; toolbar "1 selected" + 3 actions — fine |
| Feed dark · Settings dark | `d-feed`, `d-settings` | fine, contrast OK, delete icon in a lighter red |
| Compact view | `p-compact` | bookmarks with no image keep an empty thumbnail-sized gap (EYE-05) |
| Tablet feed (3 columns) | `t-feed` | fine |
| Tablet reader | `t-reader` | text runs the full 1280 dp width, ~200 characters per line (EYE-01) |
| Tablet settings | `t-settings` | title at the left edge, settings column centred (EYE-06) |

**a11y state (R5):** selection state is exposed: the selected card reads `C✓ ON`. But **every** card is also a checkable `off` outside selection mode, and its name is "Bookmark image" (EYE-04). 0 crashes, 0 ANR (`ui.py crashes`).

## Findings — all P2, all to the queue (fix severe)

| ID | Sev | What happens | Evidence | Status |
|---|---|---|---|---|
| T-02 | **P2** (workaround: open Settings → Manage tags) | **The tag filter keeps tags deleted on the server and never learns new ones.** The feed only asks the server for tags when its local list is empty. `qa_off`, `qa_off2` (deleted on the server on 2026-09-15) and a local-only `qa_c1` (id −1) were still offered on 2026-09-24. Picking one filters to an empty list; a tag made on the web can't be picked at all. Opening Manage tags fetched and pruned them. Missed last time: the first campaign's gates never looked at the sheet after a server-side delete | UI `p-filter` · STORE `tags` had ids −1, 9, 10 · API `/api/v1/tags` had 8 tags, no `qa_` · after Manage tags STORE had 0 `qa%` rows · `FeedViewModel.kt:209-212` (`if (_tagsState.value.data.isNullOrEmpty()) getRemoteTags()`) | queue |
| EYE-01 | P2 | Reader text almost touches the screen edges on a phone (~9 dp); on a tablet it spans the whole width | `p-reader`, `t-reader` | queue |
| EYE-02 | P2 · cause unproven | An inline image in the reader shows as a broken-image icon with its alt text (Kotlin docs, "Get started with coroutines") | `p-reader`, `t-reader` · could be the page's relative `src` rather than the app | queue: unproven |
| EYE-03 | P2 | Update-cache dialog: the question is a 3-line headline and Cancel is a filled button as prominent as Update; every other dialog uses a title + text buttons | `p-update` | queue |
| EYE-04 | P2 (a11y) | With TalkBack every card is "Bookmark image, not checked": the card is a checkable node even outside selection mode, and its name is the image's generic description | dump `C off ("Bookmark image")` on every card · `BookmarkImageView.kt:61` | queue |
| EYE-05 | P2 | Compact view: a bookmark with no image keeps an empty 80 dp square before its title | `p-compact` rows 3–7 | queue |
| EYE-06 | P2 | Tablet settings: "Settings" sits at the left edge while its column is centred | `t-settings` | queue |
| EYE-07 | P2 (wording) | Filter sheet titled "Categories" while every other screen says "tags" (`CategoriesView.kt:130`). "Delete this bookmark?" doesn't name it or say it's permanent (there is no trash); the tag dialog does both | `p-filter`, `p-delete` vs `p-tagdelete` | queue (product: wording) |

## Gate 01
No code changed in this process, so no test ran; last green at `f993848` (332/0). No fixtures. Device put back: phone size, demo off, theme Auto, compact off. **Closed.**

# Apple's sizes and limits

As they stood in October 2026. Apple changes them: before the first render, open Apple's pages and check, and correct
`store/store.config.json` (and this page) when they differ.

- What each asset is for, and how Apple wants it made: <https://developer.apple.com/app-store/asset-best-practices/>
- Screenshots: <https://developer.apple.com/help/app-store-connect/reference/screenshot-specifications>
- App previews:
  <https://developer.apple.com/help/app-store-connect/reference/app-information/app-preview-specifications>
- Header and search-results video ("creative assets"):
  <https://developer.apple.com/help/app-store-connect/reference/app-information/creative-assets-specifications/>
- Texts and other properties: <https://developer.apple.com/help/app-store-connect/reference/app-information>

If an address has moved, search Apple's App Store Connect help for the page's title.

## Pictures and video

| Asset | Size | Format | Notes |
|---|---|---|---|
| iPhone screenshots | portrait, one accepted size of one display class is enough: 1320 × 2868 (6.9-inch), 1206 × 2622 (6.3-inch) and their siblings | `.png` or `.jpg`, no alpha | one to ten per language; the store scales them for the other iPhones; the first ones show in search results |
| Product page header | 21:9, exactly 3840 × 1646 | `.png` or `.jpg`, no alpha | an iPhone shows the full height and about the middle 84% of the width |
| Search-results video | 3:2, from 1920 × 1280 to 3840 × 2560, 5 to 30 seconds, 30 or 60 fps | `.mov`, `.m4v` or `.mp4` | muted in search results; make it loop |
| iPad screenshots | only if the app runs on iPad: 2064 × 2752 (13-inch) and siblings | as above | a set of its own: an iPad screen is not a stretched phone screen |
| App previews | optional; per display class, for an iPhone 886 × 1920, for an iPad 1200 × 1600; 15 to 30 seconds, at most 30 fps, at most 500 MB | `.mov`, `.m4v` or `.mp4` (H.264), or ProRes 422 HQ in `.mov` | up to three per display size and language; screen captures of the app, recorded by the owner; this skill does not render them |

## Screenshots, platform by platform

The owner chooses the platforms and between the minimum and every size in stage 1 (`discover.md`). The minimum is one
set per platform at the size below, in the frame's CSS px and scale for `store/store.config.json`; the store scales it
down for the smaller displays of that platform. Every size is one set more per display class on Apple's page.

| Platform | The minimum | As a frame | Every size adds |
|---|---|---|---|
| iPhone | 1320 × 2868 (6.9-inch) | 440 × 956 at 3 | the 6.5-inch, 6.3-inch and 6.1-inch classes (the same shape, a few px apart) and the home-button classes (16:9, a layout of their own) |
| iPad | 2064 × 2752 (13-inch), required when the app runs on iPad | 1032 × 1376 at 2 | the 11-inch class and the older ones |
| Mac | one 16:10 size, 2880 × 1800 the largest | 1440 × 900 at 2 | nothing: one size is all the store takes |
| Apple TV | 3840 × 2160, or 1920 × 1080 | 1920 × 1080 at 2 | nothing |
| Apple Vision Pro | 3840 × 2160 | 1920 × 1080 at 2 | nothing |
| Apple Watch | one size, the same in every language; 422 × 514 is the largest | 211 × 257 at 2 | nothing: the store takes one size |

Apple's page also lists the iPhone with two displays (iPhone Duo) with sizes of its own and a date from which its
screenshots are required: read it there. The header and the search-results video are shown on iPhone and iPad only;
the other platforms have screenshots and app previews.

## Texts, per language

| Field | Limit | Where the store uses it |
|---|---|---|
| Name | 30 | everywhere; searched |
| Subtitle | 30 | under the name; searched |
| Promotional text | 170 | above the description; can change without a new version |
| Keywords | 100, comma-separated, no spaces after commas | searched, never shown |
| Description | 4000 | the page; not searched |
| What's New | 4000 | from the second version on |
| Support URL, Marketing URL, Privacy Policy URL | an address each | per language: point each at that language's page |

## Test information (TestFlight)

| Field | Limit |
|---|---|
| Beta App Description | 4000 |
| What to Test (per build) | 4000 |
| Feedback Email, Marketing URL, Privacy Policy URL | |
| Beta App Review Information: contact name, phone, e-mail; sign-in details if the app needs them; notes (4000) | English is safest for the notes |

## The languages the store knows

`SKILL_DIR/tools/store.py` has the list with the name App Store Connect shows for each. Two things to remember: the store's
Latin American Spanish is listed as "Spanish (Mexico)", and English has four entries (U.S., U.K., Australia, Canada)
that fall back to one another, so one English is usually enough.

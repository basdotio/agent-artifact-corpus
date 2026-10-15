# Stage 1: discover

Goal: know the product well enough to write its claims, know whether it has a design system, know which platforms
and how many display sizes the owner wants pictures for, and have a `store/` folder the renderers run on. Nothing is
designed in this stage.

## 1. Ask for the design project

Ask the owner to open their Claude Design project in this session's browser pane (signed in by themselves) and to give
you its address (`https://claude.ai/design/p/<id>`). If they have none, ask whether they want to make one now (create
an empty project and come back with its address) or work without Claude Design; both paths are in `claude-design.md`.
While they do that, read the repository.

## 2. Read the repository

Read, do not skim; write nothing yet.

- **What the product is**: README, product or vision documents, onboarding screens, an existing store listing, a
  marketing site. You are looking for the one sentence a stranger would repeat, the two or three things that make it
  unlike its neighbours, what it deliberately does not do, and who it is for.
- **How it speaks**: the app's texts (a String Catalog `*.xcstrings`, `*.strings`, `strings.xml`, ARB, i18n JSON).
  Note the tone (formal or not, praise or none, exclamation marks or none) and any rule the project states about it.
  The store's texts will follow the same rules.
- **Which languages it speaks**: the localizations that exist, and which one is the source.
- **Which screens matter**: the first launch, the main screen, the one screen that shows the product's idea, the
  screen after the job is done. Read the views, not only their names; if UI tests save screenshots, look at them.
- **The design system**: tokens (CSS variables, a theme file, an asset catalog's colours, a Tailwind configuration),
  fonts, components. Note where the colours and type sizes really come from.
- **What is already there**: an icon, a slogan, earlier screenshots, a privacy policy and its address, a support
  address. `PrivacyInfo.xcprivacy` if it is an iOS app: stage 7 answers Apple's privacy questions from it.
- **The identifiers**: bundle identifier, version, the app's name as the store will show it.

## 3. Read the design project

In the browser pane, with the owner signed in (`claude-design.md`, "Reading a project"): which pages exist, whether
there is a kit (a tokens file and a components file, usually with a showcase page), which screens are drawn. Compare
with the repository: is the kit in the project the same one the app is built from, or older?

Three outcomes:

1. **A kit exists in the project.** Export it into `store/kit/` and use it for everything.
2. **A design system exists in the code only** (a theme file, an asset catalog). Offer to turn it into a small CSS kit
   in the design project first: the tokens as CSS variables under the names the code uses, and the handful of
   components the store screens need (the app's main card or cell, its buttons, a navigation bar, a list row). That is
   one brief of its own, on a new page; the store pages come after.
3. **Nothing exists.** Say so plainly: the store pictures need a look, and the look has to be the app's. Offer to
   derive a kit from the running app (its colours, fonts and one or two screens) and have the owner approve it before
   any frame is drawn.

Never fall back to the placeholder kit of the starter for anything the owner will approve.

## 4. Ask which platforms and how many sizes

The owner answers this before anything is designed, because the answers multiply the work of every later stage. Come
with what the project says (in an Xcode project `SUPPORTED_PLATFORMS` and `TARGETED_DEVICE_FAMILY`, where 1 is iPhone
and 2 is iPad; a watch or a TV target) and ask the owner to confirm or correct it.

1. **Which platforms?** iPhone, iPad, Mac, Apple TV, Apple Watch, Apple Vision Pro. Every platform the app runs on has
   screenshots of its own in App Store Connect, and an iPad, a Mac or a watch screen is a design of its own, not a
   stretched phone. The header and the search-results video are one each, shown on iPhone and iPad.
2. **The necessary minimum, or every display size?** The minimum is one set per platform, at the largest display Apple
   asks for; the store scales it down for the others (`specs.md`). Every size is a set per display class: sharper on
   each device, and the only way to show a layout that differs between them. Its price is more design rounds (a
   display with another shape is a layout of its own), more renders, and more files the owner uploads by hand. Say
   the price as a number: sets × languages × frames is the count of files to upload (two sets, twelve languages and
   six frames are 144). Recommend the minimum unless the app looks different on the other displays.
3. **App previews?** Optional videos of the app in use, up to three per display size and language (`specs.md`). App
   Review expects screen captures of the app itself, so the owner records them; you plan them with the owner, check
   the files and put them on the upload checklist. The video this skill renders is the search-results one, another
   asset.

Write the answers into `store/PROGRESS.md` in the owner's words. Stage 2 designs the first set, then one set more for
every other platform or size chosen here (`frames.md`, "More sets"). Apple's own guide to what each asset is for:
<https://developer.apple.com/app-store/asset-best-practices/>.

## 5. Set up the store folder

Copy `SKILL_DIR/starter/` to `store/`. If `store/` is taken, ask for another name, put `STORE_DIR=<that folder>` in front
of every command, and read "store/" in these pages and in the two briefs as that folder. Then:

- `store/store.config.json`: `app` (the name), `source` (the source language's code), `languages` (only the source
  for now), `design.project` (the address), `design.kit` (the kit's files in the project).
- Once the kit is exported: `css` pointing at it, `fontLinks` (the kit's web fonts, if any), `fontVariables` (the
  kit's font variables and the faces they name, so that Japanese or Arabic can put a system face behind them),
  `rootAttributes` (what the kit expects on a root element: a class, a theme attribute), `balance` (the kit's title
  and hint classes).
- The app's texts for the checkers: `python3 SKILL_DIR/tools/app-texts-xcstrings.py <catalog>…` for String Catalogs, all
  of the app's catalogs in one call; for any
  other format write the few lines that produce the same `store/app-texts/<code>.json` (an object from key to text,
  a list where a text has several forms) and keep that script in `store/`.
- Add `store/out/` to `.gitignore` unless the owner wants the rendered files in the repository (large videos do not
  belong there in any case).
- Run the three renderers once on the untouched starter to prove the tools work. Do not show these pictures as a
  proposal: they are placeholders.

Language codes are lower case and are the folder names everywhere: `en`, `de`, `pt-br`, `es-419`, `zh`, `zh-hant`.
`SKILL_DIR/tools/store.py` lists the ones App Store Connect knows.

## 6. Report and write the ledger

Write `store/PROGRESS.md`:

```
# Store page: progress

## Product
<the one sentence> · for whom · what it is not · tone rules

## Design
project: <address> · kit: <where> · state: <exported on … | to be built>

## Platforms and sizes
<platforms> · <the minimum | every display size: which sets> · app previews: <no | the owner records them>

## Stages
- [x] 1 discover (<date>)
- [ ] 2 frames
…

## Decisions (the owner's words, dated)
## Open
## Not checked by anyone
```

Then tell the owner, in their language and in under a minute of reading: what you understood the product to be (so
they can correct you now), what the design situation is and what you propose to do about it, which platforms and
sets of sizes the pictures will be made for, which screens you would show, and what stage 2 will ask of them.

# Stage 8: the owner uploads the pictures and the video

Uploading files is the owner's step: the browser pane does not hand files to a page, and the store's own preview is
where the owner should see each asset for the first time anyway. Your part is to make it a ten-minute job per language
and to check the result with them.

## 1. Prepare

- Upload from `store/approved/<code>/`, the copies taken when the owner accepted each language (render and have
  accepted whatever is missing; `store/out/` is only where the renderers write). Every language of
  `store/store.config.json` has there:
  `frame-1.png` … `frame-<n>.png`, `header.png`, `search-video.mp4` (and `search-video-3840.mp4` if the large one was
  made), and a folder per further set of screenshots (`<code>/ipad/frame-1.png` …) for every other platform or display
  size the owner chose in stage 1.
- App previews, if the owner chose to record them: check each file against `specs.md` with `ffprobe` (size, length,
  frame rate) and list it under its language and display size.
- Check the files, not the logs: every picture has the size the store wants and no alpha channel, every video has the
  expected length and frame count (`ffprobe`), nothing is zero bytes, no language is missing a frame.
- Write `store/UPLOAD.md`: a checklist with one block per language, in the order of the language menu in App Store
  Connect, with the store's name of the language, the folder, the files in upload order, and the boxes to tick: one
  for each set of screenshots (named as App Store Connect names that platform and display size), header, video. Put the folder's full path there, so it can be pasted into the file dialog
  (in macOS: Shift-Command-G).

## 2. Tell the owner how

In their language, short:

1. App Store Connect → the app → the iOS version's page. Pick the language at the top of the page.
2. **Screenshots**: in the iPhone section, the display size the frames were rendered for; every further set in the
   section of its own platform and display size. Drag `frame-1.png` to
   `frame-<n>.png` in, then check their order on the page and drag them into place: the first ones are what search results show.
   If a set is already there, remove it first or the new ones are appended.
3. **Header** and **search-results video**: each has its own slot on the same page. Upload `header.png` and
   `search-video.mp4`. If the large video is refused, use the 1920 × 1280 one.
4. **Save**, then switch to the next language. A language with no pictures of its own shows the primary language's.
5. For each asset, open the preview App Store Connect offers and look at it on the iPhone layout.

A video takes a while to process after upload; a "processing" badge is normal.

## 3. Look at the previews together

Ask the owner to tell you (or to show you, in the pane) what the previews look like, at least for the source language,
one long-worded language and one right-to-left language if there is one:

- header: is the slogan whole, is anything under the back or share button;
- video: is any text or card cut, does the loop jump;
- screenshots: the right order, the first claim readable in the search-results layout.

What the preview crops is the only real measurement of the safe areas. If something is cut: fix it in the template or
the texts, render, compare the files that should not have changed with their approved copies
(`node SKILL_DIR/tools/compare.mjs`), replace the approved copy of the one that should, and have that file uploaded again. Record
the measured numbers in `store/store.config.json` (`header.visible`) and in `store/PROGRESS.md`, so the next render
warns about it.

## 4. Close

Update `store/CONNECT.md` ("Left for the owner": what remains is theirs alone: publishing the privacy answers,
testers, the submission) and `store/PROGRESS.md`. Then the last report: what is in the store's record now, what was
checked by whom, and what nobody has checked: texts read only by models, pictures in languages nobody previewed,
platforms and display sizes that got no set of their own and show a scaled one.

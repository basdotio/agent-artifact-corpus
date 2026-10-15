---
name: paper-figures
description: Use a cited paper's own figure - extract it from the paper's arXiv source, or crop it from papers/<bibkey>.pdf, into figures/papers/<bibkey>-fig<N>.pdf (a document) or .svg (a slide). Use whenever a slide or a note should show a figure from a paper; never redraw a look-alike.
---

# A paper's figure: the original, as PDF or SVG

A figure that shows another paper's result is shown as **that paper's own
figure**. Drawing an imitation of it in `figures/src/` is not
allowed: our own pages are only for our derivations and our own computed
numbers.

```sh
python3 .github/tools/figures/paper_figures.py <bibkey> [--svg]                              # every figure, from the arXiv source
python3 .github/tools/figures/paper_figures.py <bibkey> 1 4 [--svg]                          # only Figs. 1 and 4
python3 .github/tools/figures/paper_figures.py <bibkey> crop <N> <page> <x> <y> <w> <h> [--svg]  # from papers/<bibkey>.pdf
```

Two uses, two formats, flat in `figures/papers/`. Decide which one first and
keep only that one for a figure:

| Used in | Format | File |
|---|---|---|
| a LaTeX document (notes, paper) | **PDF**, the default | `<bibkey>-fig<N>.pdf` |
| a slide or a storyboard page | **SVG**, with `--svg` | `<bibkey>-fig<N>.svg` |

A figure built from several files is `<bibkey>-fig<N>a`, `…b`, in include
order.

- **PDF** carries no caption. The caption is printed when a figure is
  extracted; read it there or in the paper (`pdftotext papers/<bibkey>.pdf - | grep -A2 'FIG. '`)
  and write the caption of the document by hand.
- **SVG** carries the figure's label and caption in its `<desc>`, so a figure
  is found by what it shows:

  ```sh
  grep -o '<desc>[^<]*' figures/papers/<bibkey>-fig*.svg | cut -c1-200
  ```

A figure that nothing includes or links is deleted.

## Which route

1. **arXiv source** (default). The key's `eprint`, or `doiget link <doi>`,
   gives the id. Figures are numbered by the order of the figure environments
   in the main `.tex` (inputs inlined) — the paper's own numbering. Check one
   against the PDF (`FIG. N.` in `pdftotext papers/<bibkey>.pdf`) the first time.
   Vector figures (pdf, eps) stay vector; png/jpg are saved as a PDF page (SVG: embedded unchanged).
2. **Crop** (no arXiv source: old or publisher-only papers). Render the page at
   72 dpi, where one pixel is one PDF point, and read off the box:
   ```sh
   pdftocairo -png -r 72 -f <page> -l <page> papers/<bibkey>.pdf /tmp/p
   ```
   Then `crop <N> <page> <x> <y> <w> <h>` (whole numbers, top-left origin). The result is a
   vector crop of the printed page — look at it before using it.

## Using it

- **LaTeX.** Include the PDF like any figure
  (`\includegraphics{papers/<bibkey>-fig<N>}` with `\graphicspath{{figures/}}`),
  and cite the paper wherever it is shown — the figure is the authors' work.
  A vector crop keeps everything the page drew and can be heavy. For a crop
  above a few hundred kB, render the same box with `pdftoppm -png -r 300 -x -y
  -W -H` (in pixels) and save the PNG as a PDF.
- **Slides.** Link the SVG like any figure
  (`../../figures/papers/<bibkey>-fig<N>.svg`), with a `<cite>` to the same
  key right under it on a storyboard page, or the citation beside the figure in
  the deck style. Glyphs are paths, so no fonts are needed.
- Take only the figures that are used (give their numbers). Re-running with
  numbers replaces just those; without numbers, every `-fig*` of that format
  for the key is rewritten. Never edit these files by hand.
- To find the number first, read the captions in the PDF
  (`pdftotext papers/<bibkey>.pdf - | grep -A2 'FIG. '`).

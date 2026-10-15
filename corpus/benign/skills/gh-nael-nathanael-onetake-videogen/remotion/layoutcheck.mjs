// Renders chosen frames of a composition with the layout report on (src/layoutReport.tsx) and prints
// the reports as "LAYOUTCHECK [json]". Run by scripts/check.py; lives here so Node finds the Remotion
// packages. Reading measurements from the page through onBrowserLog follows Alain00/blobatar
// (apps/video/scripts/check-gaze.ts).
//
//   node layoutcheck.mjs COMP FRAMES [--props FILE] [--stills DIR]
//
// FRAMES is a comma-separated list of frame numbers. --stills keeps each frame as DIR/fNNNN.jpg, so the
// pass that checks the layout also gives the stills to look at.
import { bundle } from "@remotion/bundler";
import { openBrowser, renderStill, selectComposition } from "@remotion/renderer";
import { existsSync, mkdirSync, mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { parseArgs } from "node:util";

const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: { props: { type: "string" }, stills: { type: "string" } },
});
const [comp, frameList] = positionals;
if (!comp || !frameList) throw new Error("usage: node layoutcheck.mjs COMP FRAMES [--props FILE] [--stills DIR]");

const inputProps = { ...(values.props ? JSON.parse(readFileSync(values.props, "utf8")) : {}), layoutReport: true };
const outDir = values.stills ? resolve(values.stills) : mkdtempSync(join(tmpdir(), "layoutcheck-"));
mkdirSync(outDir, { recursive: true });

// Same browser choice as remotion.config.ts, which the Node API does not read.
const chrome = process.env.REMOTION_BROWSER_EXECUTABLE ?? "/usr/bin/google-chrome";
const browserOptions = existsSync(chrome) ? { browserExecutable: chrome, chromeMode: "chrome-for-testing" } : {};

const serveUrl = await bundle({ entryPoint: resolve(import.meta.dirname, "src/index.ts") });
const browser = await openBrowser("chrome", { ...browserOptions, logLevel: "error" });
const reports = [];
try {
  const composition = await selectComposition({ serveUrl, id: comp, inputProps, puppeteerInstance: browser, ...browserOptions });
  for (const frame of frameList.split(",").map(Number)) {
    if (!(frame >= 0 && frame < composition.durationInFrames)) {
      throw new Error(`frame ${frame} is outside ${comp} (0-${composition.durationInFrames - 1})`);
    }
    let report = null;
    await renderStill({
      composition,
      serveUrl,
      inputProps,
      frame,
      output: join(outDir, `f${String(frame).padStart(4, "0")}.jpg`),
      imageFormat: "jpeg",
      puppeteerInstance: browser,
      logLevel: "error",
      onBrowserLog: (log) => {
        if (log.text.startsWith("[layout] ")) report = JSON.parse(log.text.slice("[layout] ".length));
      },
      ...browserOptions,
    });
    if (!report) throw new Error(`${comp} frame ${frame} sent no layout report: register its component through \`checked\` in src/Root.tsx`);
    reports.push(report);
  }
} finally {
  await browser.close({ silent: true });
}
// Remotion echoes the page's console to stdout too; the prefix marks the line that is the result.
console.log(`LAYOUTCHECK ${JSON.stringify(reports)}`);

// Starter for one flow video. Copy next to your outputs, rename, replace the steps. Run with Node, not Bun.
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

// Absolute path of this skill's scripts/vlib.mjs; the skill tells you where it lives.
const VLIB = "<skill-dir>/scripts/vlib.mjs";
const { consoleErrors, finishVideo, launch, openTab, plainPage, recordedPage, say, signIn } = await import(
  pathToFileURL(VLIB).href
);

const OUT = path.dirname(fileURLToPath(import.meta.url));
const NAME = "flow-name";
// Read the test password from the project's seed or fixture file; never paste it here.
const password = process.env.TEST_PASSWORD;

const browser = await launch();

// Setup the viewer should not watch (seeding, other accounts) runs on a plain page first.
const setup = await plainPage(browser);
await setup.context().close();

const page = await recordedPage(browser, OUT, NAME);
try {
  await signIn(page, { email: "admin@example.test", password, next: "/staff" });
  await openTab(page, "People");
  await say(page, "What the viewer is looking at, in plain words.", 3000);
} finally {
  await finishVideo(page, OUT, NAME);
  await browser.close();
  console.log(consoleErrors.length ? consoleErrors.join("\n") : "no console errors");
}

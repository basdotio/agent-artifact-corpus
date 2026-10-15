import { Config } from "@remotion/cli/config";
import { existsSync } from "node:fs";

// Prefer an already-installed Chrome (REMOTION_BROWSER_EXECUTABLE, or the usual Linux path)
// so no extra browser is downloaded. Without one, Remotion fetches its own headless shell.
const browser = process.env.REMOTION_BROWSER_EXECUTABLE ?? "/usr/bin/google-chrome";
if (existsSync(browser)) {
  Config.setBrowserExecutable(browser);
  Config.setChromeMode("chrome-for-testing");
}
Config.setConcurrency(Number(process.env.REMOTION_CONCURRENCY ?? 8));

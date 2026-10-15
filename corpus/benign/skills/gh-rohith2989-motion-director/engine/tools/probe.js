// Evaluate an expression in the composition at time t, or save a screenshot:
//   node tools/probe.js 12.5 "document.querySelectorAll('.scene').length"
//   node tools/probe.js 12.5 "shot:renders/probe.png"
//   node tools/probe.js 0 "window.getCues()" > audio/cues.json        (every sound cue, sorted)
// PAGE / QUERY env vars select another entry page or ?only= subset.
const puppeteer = require("puppeteer");
const fs = require("fs");
const path = require("path");
const { start, ROOT } = require("./server");

(async () => {
  const [t, expr] = process.argv.slice(2);
  const config = JSON.parse(fs.readFileSync(path.join(ROOT, "comp", "config.json"), "utf8"));
  const server = await start(0);
  const port = server.address().port;
  const browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH || undefined, headless: true, defaultViewport: { width: config.width, height: config.height } });
  let failed = null;
  try {
    const page = await browser.newPage();
    page.on("pageerror", (e) => {
      console.error("[pageerror]", e.message);
      failed = failed || e;
    });
    const q = process.env.QUERY ? `?${process.env.QUERY}` : "";
    await page.goto(`http://127.0.0.1:${port}/${process.env.PAGE || "comp/index.html"}${q}`, { waitUntil: "load" });
    const t0 = Date.now();
    while (!(await page.evaluate(() => window.__ready === true))) {
      if (failed) throw failed;
      if (Date.now() - t0 > 120000) throw new Error("boot timeout");
      await new Promise((r) => setTimeout(r, 100));
    }
    await page.evaluate((tt) => window.renderAt(tt), Number(t));
    if (expr.startsWith("shot:")) {
      await page.screenshot({ path: expr.slice(5), type: "png" });
      console.error("saved", expr.slice(5));
    } else console.log(JSON.stringify(await page.evaluate(expr), null, 1));
  } catch (e) {
    console.error(e.message || e);
    process.exitCode = 1;
  }
  const proc = browser.process();
  await Promise.race([browser.close().catch(() => {}), new Promise((r) => setTimeout(r, 5000))]);
  try { if (proc && proc.exitCode === null) proc.kill("SIGKILL"); } catch {}
  server.close();
  process.exit(process.exitCode || 0);
})();

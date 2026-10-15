// Entry: load the voice timeline if there is one, import the scenes (in order, or a ?only=s01,s03 subset
// while building), boot, and (with ?debug) mount the scrubber. Rendering drives window.renderAt(t).
import { boot, mountDebug, CONFIG } from "./core/runtime.js";
import { loadVO } from "./sys/vo.js";
import { SCENES } from "./scenes/index.js";

if (CONFIG.narrated) await loadVO(); // comp/data/vo.json, built by voice/vo_build.py
const q = new URLSearchParams(location.search);
const only = q.get("only");
for (const m of SCENES) {
  if (only && !only.split(",").some((k) => m.startsWith(k))) continue;
  await import(`./scenes/${m}.js`);
}
await boot();
if (q.has("debug")) mountDebug();

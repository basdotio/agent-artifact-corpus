#!/usr/bin/env node
// Says whether two pictures are the same picture, pixel for pixel: for proving that a change to a script, a template
// or the kit left an approved render as it was.
// Usage: node compare.mjs <one.png> <other.png>         exit code 0 when no pixel differs
import { sharp } from "./lib.mjs";

const [one, other] = process.argv.slice(2);
if (!one || !other) { console.error("usage: node compare.mjs <one.png> <other.png>"); process.exit(2); }
const raw = async (file) => sharp()(file).removeAlpha().raw().toBuffer({ resolveWithObject: true });
const a = await raw(one), b = await raw(other);
if (a.info.width !== b.info.width || a.info.height !== b.info.height) {
  console.log(`different sizes: ${a.info.width} x ${a.info.height} and ${b.info.width} x ${b.info.height}`);
  process.exit(1);
}
let differing = 0, most = 0;
for (let i = 0; i < a.data.length; i += 3) {
  const d = Math.max(Math.abs(a.data[i] - b.data[i]), Math.abs(a.data[i + 1] - b.data[i + 1]), Math.abs(a.data[i + 2] - b.data[i + 2]));
  if (d) { differing++; if (d > most) most = d; }
}
console.log(differing ? `${differing} of ${a.data.length / 3} pixels differ (by ${most} of 255 at most)` : "the same picture: no pixel differs");
process.exit(differing ? 1 : 0);

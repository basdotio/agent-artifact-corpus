import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { jevModulePath, loadJev } from "./load-jev.ts";

function withEnv(vars: Record<string, string | undefined>, fn: () => Promise<void> | void) {
  const saved: Record<string, string | undefined> = {};
  for (const k of Object.keys(vars)) saved[k] = process.env[k];
  const restore = () => {
    for (const [k, v] of Object.entries(saved)) {
      if (v === undefined) delete process.env[k];
      else process.env[k] = v;
    }
  };
  for (const [k, v] of Object.entries(vars)) {
    if (v === undefined) delete process.env[k];
    else process.env[k] = v;
  }
  let r: Promise<void> | void;
  try {
    r = fn();
  } catch (e) {
    restore();
    throw e;
  }
  return Promise.resolve(r).finally(restore);
}

void test("STYLE_GUIDE_JEV_MODULE があればそれを返し、loadJev で読める", async () => {
  const dir = mkdtempSync(join(tmpdir(), "sg-jev-"));
  const file = join(dir, "fake.mjs");
  writeFileSync(file, 'export const DEFAULT_ENDPOINT="x";\n');
  await withEnv({ STYLE_GUIDE_JEV_MODULE: file }, async () => {
    assert.equal(jevModulePath(), file);
    const mod = await loadJev();
    assert.ok(typeof mod === "object" && mod !== null && "DEFAULT_ENDPOINT" in mod);
    assert.equal(mod.DEFAULT_ENDPOINT, "x");
  });
});

void test("共通ディレクトリが無ければ同梱の lib/jev.mjs を返す", async () => {
  const home = mkdtempSync(join(tmpdir(), "sg-home-"));
  await withEnv({ STYLE_GUIDE_JEV_MODULE: undefined, HOME: home, USERPROFILE: home }, () => {
    const bundled = join(dirname(fileURLToPath(import.meta.url)), "jev.mjs");
    assert.equal(jevModulePath(), bundled);
  });
});

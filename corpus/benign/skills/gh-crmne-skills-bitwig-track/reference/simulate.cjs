// Runs the generated controller script against a fake Bitwig host: a small
// model of a project (tracks, devices, launcher clips, cue markers, transport)
// where every action lands after a delay, like the real thing. It presses
// Build twice (the second must change nothing but the clips), then Markers,
// then Lengths, then Record, and checks the result against score.json.
//
//   node bitwig/simulate.cjs [script.control.js] [score.json]
//
// With no arguments it runs the one generated *.control.js next to it (not
// the template) against ../score.json (or ./score.json). If the presets in
// score.json aren't installed on this computer, set
// SIM_ALLOW_MISSING_PRESETS=1 to check everything else.
//
// It can't hear anything or prove Bitwig accepts every call; it proves the
// script's sequencing, lookups, and idempotency, and that every value it reads
// was marked interested in init() (Bitwig throws otherwise).
//
// It models what happened in Bitwig 6.1.1: createEmptyClip makes a one-bar
// clip whatever length it's asked for, and sets on the clip's range are
// dropped unless the value was subscribed (markInterested) in init(). With
// SIM_REFUSE_LENGTH=1 range sets are ignored outright, which forces the
// duplicateContent fallback.

"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");

const here = __dirname;
function defaultScript() {
  const found = fs.readdirSync(here).filter(f => f.endsWith(".control.js") && f !== "template.control.js");
  if (found.length !== 1) throw new Error("pass the script to simulate; found " + (found.join(", ") || "no generated script") + " in " + here);
  return path.join(here, found[0]);
}
function defaultScore() {
  for (const p of [path.join(here, "..", "score.json"), path.join(here, "score.json")]) if (fs.existsSync(p)) return p;
  throw new Error("pass score.json; none found next to or above " + here);
}
const scriptPath = path.resolve(process.argv[2] || defaultScript());
const score = JSON.parse(fs.readFileSync(path.resolve(process.argv[3] || defaultScore()), "utf8"));
const ALLOW_MISSING_PRESETS = process.env.SIM_ALLOW_MISSING_PRESETS === "1";
const missingPresets = new Set();

// ------------------------------------------------------------ virtual time
let now = 0;
let queue = [];
function schedule(fn, ms) { queue.push({ at: now + Math.max(0, ms), fn, seq: queue.length + now * 1e6 }); }
function tick() {
  // Transport advances with time
  if (project.playing) project.position += (10 / 1000) * project.tempo / 60;
}
function runUntilIdle(limitMs) {
  const end = now + limitMs;
  while (now < end) {
    queue.sort((a, b) => a.at - b.at || a.seq - b.seq);
    const due = queue.filter(e => e.at <= now);
    queue = queue.filter(e => e.at > now);
    for (const e of due) e.fn();
    if (!queue.length && !project.playing) return;
    now += 10;
    tick();
  }
  throw new Error("simulation did not settle in " + limitMs + " ms");
}

// ------------------------------------------------------------ the project
const project = {
  tempo: 120, timeSig: "4/4", position: 0, playing: false, arrangerRecord: false, preRoll: "one_bar",
  tracks: [{ name: "Inst 1", devices: [], slot: null, sends: {} }, { name: "Audio 1", devices: [], slot: null, sends: {} }],
  fx: [], master: [], markers: [], selected: null, recorded: [], launched: false,
};
const LAG = 120; // ms for anything the engine does
const REFUSE_LENGTH = process.env.SIM_REFUSE_LENGTH === "1";

const log = [];
const dropped = [];
const errors = [];
const popups = [];

function value(get, set, label) {
  let interested = false;
  return {
    markInterested() { interested = true; },
    get() { if (!interested) throw new Error("value read without markInterested: " + label); return get(); },
    getRaw() { if (!interested) throw new Error("value read without markInterested: " + label); return get(); },
    set(v) { if (this.dropUnlessInterested && !interested) { dropped.push(label); return; } schedule(() => set(v), 20); },
    setRaw(v) { this.set(v); },
    addValueObserver() {},
  };
}

const fnv = v => () => v;

function deviceBank(list, label) {
  const items = {};
  return {
    getItemAt(i) {
      if (!items[i]) {
        items[i] = {
          exists: fnv(value(() => !!list()[i], () => {}, label + " device exists " + i)),
          name: fnv(value(() => (list()[i] || {}).name || "", () => {}, label + " device name " + i)),
        };
      }
      return items[i];
    },
  };
}

function presetDevice(file) {
  if (!fs.existsSync(file)) {
    assert(ALLOW_MISSING_PRESETS, "preset missing: " + file + " (SIM_ALLOW_MISSING_PRESETS=1 to carry on)");
    missingPresets.add(file);
  }
  const device = file.split("/Presets/")[1] ? file.split("/Presets/")[1].split("/")[0] : "Polymer";
  return { name: device, preset: file };
}

function channel(getList, i, label) {
  const t = () => getList()[i];
  let slotItem = null;
  const slotBank = {
    getItemAt() {
      return slotItem || (slotItem = {
        hasContent: fnv(value(() => !!(t() && t().slot), () => {}, label + " hasContent " + i)),
        select() { schedule(() => { project.selected = t(); }, LAG); },
        showInEditor() {},
      });
    },
    // Bitwig 6.1.1 made one-bar clips here regardless of the length asked for.
    createEmptyClip(slot, len) { schedule(() => { t().slot = { asked: len, playStart: 0, playStop: 4, loopStart: 0, loopLength: 4, notes: new Map(), loop: true, name: "" }; }, LAG); },
    deleteClip() { schedule(() => { t().slot = null; if (project.selected === t()) project.selected = null; }, LAG); },
  };
  const sends = {
    getItemAt(j) {
      return { value() { return { set(v) { schedule(() => { t().sends[project.fx[j].name] = v; }, 20); } }; } };
    },
  };
  return {
    exists: fnv(value(() => !!t(), () => {}, label + " exists " + i)),
    name: fnv(value(() => (t() ? t().name : ""), v => { t().name = v; }, label + " name " + i)),
    clipLauncherSlotBank: () => slotBank,
    createDeviceBank: () => deviceBank(() => (t() ? t().devices : []), label + " " + i),
    startOfDeviceChainInsertionPoint: () => ({ insertFile(f) { const d = presetDevice(f); schedule(() => t().devices.unshift(d), LAG * 3); } }),
    endOfDeviceChainInsertionPoint: () => ({ insertFile(f) { const d = presetDevice(f); schedule(() => t().devices.push(d), LAG * 3); } }),
    sendBank: () => sends,
  };
}

function bank(getList, label) {
  const items = {};
  return { getItemAt(i) { return items[i] || (items[i] = channel(getList, i, label)); }, sceneBank: () => sceneBank };
}

const sceneBank = {
  getScene() {
    return {
      launch() {
        schedule(() => {
          project.launched = true;
          if (!project.playing) project.playing = true;
          if (project.arrangerRecord) project.recording = true;
        }, LAG);
      },
    };
  },
};

let stepObserver = null;
const cursorClip = {
  getTrack() { return this.track || (this.track = { name: fnv(value(() => (project.selected ? project.selected.name : ""), () => {}, "cursor clip track")) }); },
  addStepDataObserver(fn) { stepObserver = fn; },
  setStepSize(s) { this.step = s; },
  scrollToKey(k) { assert.strictEqual(k, 0); },
  scrollToStep(s) { assert.strictEqual(s, 0); },
  clearSteps() {
    const c = project.selected.slot;
    schedule(() => { for (const k of c.notes.keys()) { const [x, y] = k.split(":"); stepObserver(+x, +y, 0); } c.notes.clear(); }, 10);
  },
  setStep(ch, x, y, vel, dur) {
    assert(Number.isInteger(x) && x >= 0 && x < 400, "x out of the grid: " + x);
    assert(Number.isInteger(y) && y >= 0 && y < 128, "y out of range: " + y);
    assert(vel >= 1 && vel <= 127, "velocity " + vel);
    const c = project.selected.slot;
    schedule(() => { c.notes.set(x + ":" + y, { x, y, vel, dur }); stepObserver(x, y, 2); }, 30);
  },
  isLoopEnabled() { return this.range("loop"); },
  getPlayStart() { return this.range("playStart"); },
  getPlayStop() { return this.range("playStop"); },
  getLoopStart() { return this.range("loopStart"); },
  getLoopLength() { return this.range("loopLength"); },
  range(field) {
    this.ranges = this.ranges || {};
    if (!this.ranges[field]) {
      const v = value(() => (project.selected && project.selected.slot ? project.selected.slot[field] : 0),
        x => { if (!REFUSE_LENGTH || field === "loop") project.selected.slot[field] = x; }, "cursor clip " + field);
      v.dropUnlessInterested = true;
      this.ranges[field] = v;
    }
    return this.ranges[field];
  },
  duplicateContent() {
    schedule(() => {
      const c = project.selected.slot;
      const len = c.loopLength;
      for (const n of [...c.notes.values()]) c.notes.set((n.x + len / score.stepSize) + ":" + n.y, Object.assign({}, n, { x: n.x + len / score.stepSize }));
      c.loopLength = len * 2;
      c.playStop = Math.max(c.playStop, len * 2);
      project.doublings = (project.doublings || 0) + 1;
    }, LAG);
  },
  setName(n) { project.selected.slot.name = n; },
};

const markerItems = {};
const markerBank = {
  getItemAt(i) {
    if (!markerItems[i]) {
      const m = () => project.markers.slice().sort((a, b) => a.pos - b.pos)[i];
      markerItems[i] = {
        exists: fnv(value(() => !!m(), () => {}, "marker exists " + i)),
        name: fnv(value(() => (m() ? m().name : ""), v => { m().name = v; }, "marker name " + i)),
        position: fnv(value(() => (m() ? m().pos : 0), v => { m().pos = v; }, "marker position " + i)),
      };
    }
    return markerItems[i];
  },
};

const signals = {};
const host = {
  loadAPI(v) { assert(Number.isInteger(v) && v >= 1, "loadAPI(" + v + ")"); host.api = v; },
  setShouldFailOnDeprecatedUse() {},
  defineController(vendor, name, version, uuid, author) {
    assert(/^[0-9a-f-]{36}$/.test(uuid), "uuid");
    Object.assign(host, { defined: { vendor, name, version, uuid, author } });
  },
  defineMidiPorts(i, o) { assert.strictEqual(i + o, 0); },
  println(s) { log.push(s); },
  errorln(s) { errors.push(s); },
  showPopupNotification(s) { popups.push(s); },
  scheduleTask(fn, ms) { schedule(fn, ms); },
  createApplication: () => ({
    createInstrumentTrack(pos) { assert.strictEqual(pos, -1); schedule(() => project.tracks.push({ name: "Inst " + (project.tracks.length + 1), devices: [], slot: null, sends: {} }), LAG * 2); },
    createEffectTrack(pos) { assert.strictEqual(pos, -1); schedule(() => project.fx.push({ name: "FX " + (project.fx.length + 1), devices: [], slot: null, sends: {} }), LAG * 2); },
  }),
  createTransport: () => {
    const tempo = value(() => project.tempo, v => { project.tempo = v; }, "tempo");
    const playing = value(() => project.playing, () => {}, "isPlaying");
    const pos = value(() => project.position, () => {}, "playPosition");
    const rec = value(() => project.arrangerRecord, v => { project.arrangerRecord = v; }, "arranger record");
    const pre = value(() => project.preRoll, v => { project.preRoll = v; }, "preRoll");
    return {
      tempo: () => ({ value: () => tempo }),
      timeSignature: () => ({ set(v) { project.timeSig = v; } }),
      isPlaying: () => playing,
      playPosition: () => pos,
      isArrangerRecordEnabled: () => rec,
      preRoll: () => pre,
      setPosition(b) { schedule(() => { project.position = b; }, 30); },
      addCueMarkerAtPlaybackPosition() { schedule(() => project.markers.push({ name: "Marker " + (project.markers.length + 1), pos: project.position }), LAG); },
      play() { schedule(() => { project.playing = true; }, 30); },
      stop() { schedule(() => { project.playing = false; if (project.recording) { project.recorded.push(project.position); project.recording = false; } }, 30); },
      returnToArrangement() { project.backToArrangement = true; },
    };
  },
  createArranger: () => ({ createCueMarkerBank: () => markerBank }),
  createMainTrackBank: (n, s, sc) => bank(() => project.tracks, "track"),
  createEffectTrackBank: () => bank(() => project.fx, "fx"),
  createMasterTrack: () => ({
    createDeviceBank: () => deviceBank(() => project.master, "master"),
    endOfDeviceChainInsertionPoint: () => ({ insertFile(f) { const d = presetDevice(f); schedule(() => project.master.push(d), LAG * 3); } }),
  }),
  createLauncherCursorClip: (w, h) => { assert.strictEqual(w, score.lengthBeats / score.stepSize); assert.strictEqual(h, 128); return cursorClip; },
  getPreferences: () => ({
    getSignalSetting(label, category, action) {
      return { addSignalObserver(fn) { signals[action] = fn; } };
    },
  }),
};

// ------------------------------------------------------------ run it
const source = fs.readFileSync(scriptPath, "utf8");
assert(!/=>|\blet\b|\bconst\b|`/.test(source.replace(/"[^"\n]*"/g, "").replace(/\/\/.*$/gm, "")), "keep the script ES5");
const ctx = { host, println: s => log.push(s), Math, JSON, Object, String };
vm.createContext(ctx);
vm.runInContext("function loadAPI(v) { host.loadAPI(v); }\n" + source, ctx, { filename: path.basename(scriptPath) });
ctx.init();
assert.deepStrictEqual(Object.keys(signals).sort(), ["Build", "Lengths", "Markers", "Record", "Stop"]);

function press(action, ms) {
  signals[action]();
  runUntilIdle(ms);
  if (errors.length && process.env.SIM_LOG) console.log(log.join("\n"));
  assert.deepStrictEqual(errors, [], "errors after " + action + ":\n" + errors.join("\n"));
}

function check() {
  assert.strictEqual(project.tempo, score.tempo);
  for (const fx of score.fx) {
    const t = project.fx.filter(f => f.name === fx.name);
    assert.strictEqual(t.length, 1, "effect track " + fx.name);
    assert.strictEqual(t[0].devices.length, 1);
  }
  for (const part of score.tracks) {
    const t = project.tracks.filter(x => x.name === part.name);
    assert.strictEqual(t.length, 1, "one track named " + part.name);
    assert.strictEqual(t[0].devices.length, 1, part.name + " devices");
    assert.strictEqual(t[0].devices[0].preset, part.preset);
    assert(t[0].slot, part.name + " clip");
    const c = t[0].slot;
    assert.strictEqual(c.loop, false, part.name + " doesn't loop");
    assert.strictEqual(c.playStart, 0);
    if (REFUSE_LENGTH) assert(c.playStop >= score.lengthBeats, part.name + " plays the whole part (doubled): " + c.playStop);
    else assert.strictEqual(c.playStop, score.lengthBeats, part.name + " plays the whole part: " + c.playStop);
    if (!REFUSE_LENGTH) assert.strictEqual(c.loopLength, score.lengthBeats);
    assert.strictEqual(t[0].slot.notes.size, part.notes.length, part.name + " note count");
    for (const n of part.notes) {
      const got = t[0].slot.notes.get(Math.round(n[0] / score.stepSize) + ":" + n[1]);
      assert(got && got.vel === n[2] && Math.abs(got.dur - n[3]) < 1e-9, part.name + " note " + JSON.stringify(n));
    }
    for (const fx of score.fx) assert.strictEqual(t[0].sends[fx.name], part.sends[fx.name] || 0, part.name + " send " + fx.name);
  }
  assert.strictEqual(project.master.filter(d => d.name === score.master.device).length, 1, "one master compressor");
  assert.strictEqual(project.markers.length, score.cues.length, "marker count");
  for (const c of score.cues) {
    const m = project.markers.filter(x => x.name === c.name);
    assert.strictEqual(m.length, 1, "marker " + c.name);
    assert(Math.abs(m[0].pos - c.beat) < 0.01, "marker position " + c.name);
  }
  assert.strictEqual(project.tracks.length, 2 + score.tracks.length, "left the existing tracks alone");
}

press("Build", 600000);
check();
const firstLog = log.length;
press("Build", 600000);
check();
assert(log.slice(firstLog).some(l => /exists at/.test(l)), "second build reused tracks");
assert(!log.slice(firstLog).some(l => /creating/.test(l)), "second build created nothing");
project.markers.find(m => m.name === score.cues[1].name).pos += 3;   // someone dragged one
press("Markers", 60000);
check();
popups.length = 0;
const first = score.tracks[0].name;
const L = score.lengthBeats;
project.tracks.find(x => x.name === first).slot.playStop = 4;   // someone shortened one by hand
press("Lengths", 60000);
assert(popups.some(p => p.includes("1 clip(s) short: " + first + ": 4 beats")), "Check lengths reports the short clip: " + popups.join(" | "));
project.tracks.find(x => x.name === first).slot.playStop = L;
popups.length = 0;
press("Lengths", 60000);
assert(popups.some(p => p.startsWith(host.defined.name + ": all " + score.tracks.length + " clips play")), "Check lengths: " + popups.join(" | "));
const lengthLine = first + ": " + L + " beats (" + Math.round(L / 4 * 100) / 100 + " bars";
assert(log.some(l => l.includes(lengthLine)), "logs " + lengthLine);
press("Record", 200000);
assert.strictEqual(project.recorded.length, 1, "one take");
assert(project.recorded[0] >= score.lengthBeats, "recorded the whole score: " + project.recorded[0]);
assert.strictEqual(project.arrangerRecord, false, "disarmed");
assert.strictEqual(project.preRoll, "one_bar", "pre-roll restored");
assert(project.backToArrangement, "back to the arrangement");
assert.strictEqual(project.position, 0);

assert.deepStrictEqual(dropped, [], "sets on values the script never subscribed: " + dropped.join(", "));
if (process.env.SIM_LOG) console.log(log.join("\n"));
console.log(log.filter(l => /ready|loaded|done|built|recorded|doubling|took|clip lengths/.test(l) || l.includes(first + ": ")).slice(0, 40).join("\n"));
console.log(popups.join("\n"));
if (REFUSE_LENGTH) assert(project.doublings > 0, "fell back to duplicateContent");
if (missingPresets.size) console.log("\nwarning: " + missingPresets.size + " preset(s) not installed here, skipped: " + [...missingPresets].join(", "));
console.log(`\nok: API ${host.api}, ${score.tracks.length} tracks, ${score.tracks.reduce((a, t) => a + t.notes.length, 0)} notes, ` +
  `${score.cues.length} markers, idempotent rebuild, record stopped at beat ${project.recorded[0].toFixed(2)}; ` +
  `${(now / 1000).toFixed(1)} s simulated, popups: ${popups.length}`);

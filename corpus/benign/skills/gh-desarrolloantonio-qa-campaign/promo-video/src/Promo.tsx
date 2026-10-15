// Script: what it is -> how you use it -> what it does -> one real bug (order "why"),
// or the bug first as a hook (order "bug"). Style "dark" | "light" swaps the design tokens.
// Wording comes from README.md (the three findings are its "What it has found" list).
import React from "react";
import { AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame } from "remotion";
import { Bg, Caption, Fade, MONO, SANS, THEMES, ThemeProvider, clamp, useGlass, useTheme } from "./theme";
import { BlurLine, Devices, FlipCard, FlyChars, InkOpen, ShellIn, Findings, W } from "./shots";

export const TOTAL = 900;
export type Variant = { style: "dark" | "light"; order: "why" | "bug" };

const w = (s: string, c?: string): W[] => s.split(" ").map((t) => ({ t, c }));

// What it is (180f): brand-ink-open, then blur-slide headline
const Intro = () => {
  const C = useTheme();
  return (
    <AbsoluteFill style={{ justifyContent: "center", padding: "0 150px" }}>
      <InkOpen />
      <div style={{ fontFamily: SANS, color: C.ink }}>
        <BlurLine start={74} gap={3} dy={40} style={{ fontSize: 84, fontWeight: 800, letterSpacing: "-0.02em", lineHeight: 1.1, maxWidth: 1500 }}
          words={[...w("Your coding agent tests your app like a"), { t: "QA", c: C.brand }, { t: "engineer.", c: C.brand }]} />
        <BlurLine start={112} gap={2.5} dy={26} style={{ fontSize: 46, color: C.muted, marginTop: 30, maxWidth: 1500 }}
          words={w("For hours. On a real device. Then it fixes what it finds.")} />
      </div>
    </AbsoluteFill>
  );
};

// How you use it (240f): assemble-then-type-flyin
const Use = () => {
  const C = useTheme();
  const glass = useGlass();
  return (
    <AbsoluteFill>
      <ShellIn at={0} from={[0, -90]} rot={0} style={{ left: 260, top: 130, ...glass, borderRadius: 999, padding: "10px 26px", fontFamily: MONO, fontSize: 22, color: C.muted, letterSpacing: "0.12em" }}>STEP 1 · YOU RUN ONE COMMAND</ShellIn>
      <ShellIn at={4} from={[420, 40]} rot={4} style={{ left: 260, top: 200, width: 1400, height: 600, ...glass, padding: "44px 60px", boxSizing: "border-box" }}>
        <FlyChars seed="cmd" start={34} step={1.6} text="$ /qa-campaign" style={{ fontFamily: MONO, fontSize: 38, color: C.ink }} />
        <FlyChars seed="ask" start={70} step={1} text="Before I touch anything, I need to know:" style={{ fontFamily: SANS, fontSize: 32, color: C.muted, marginTop: 30 }} />
        {["• which build?", "• which devices?", "• which test accounts?", "• may I commit?"].map((t, i) => (
          <FlyChars key={i} seed={`b${i}`} start={100 + i * 16} step={1.2} text={t} style={{ fontFamily: SANS, fontSize: 36, color: C.ink, marginTop: 16 }} />
        ))}
        <FlyChars seed="end" start={175} step={0.8} text="Nothing is touched until you answer." style={{ fontFamily: SANS, fontSize: 44, fontWeight: 700, color: C.green, marginTop: 40 }} />
      </ShellIn>
    </AbsoluteFill>
  );
};

// What it does (240f): blur-slide steps + card-flip-reveal (test fails, then passes)
const Does = ({ url }: { url: boolean }) => {
  const C = useTheme();
  const glass = useGlass();
  const f = useCurrentFrame();
  const z = spring({ frame: f, fps: 30, config: { damping: 200 }, durationInFrames: 36 });
  const flipIn = interpolate(f, [150, 170], [0, 1], clamp);
  const steps = [
    { at: 16, n: "1", t: "It uses your app screen by screen: taps everything, fills every form" },
    { at: 56, n: "2", t: "It looks at every screen on phone and tablet, light and dark" },
    { at: 96, n: "3", t: "It breaks things on purpose: kills the app, cuts the network" },
    { at: 136, n: "4", t: "It checks what the server really stored, not just the screen" },
    { at: 176, n: "5", t: "It fixes what it finds, with a test it watched fail first", c: C.green },
  ];
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 160, top: 160, width: 960, height: 600, ...glass, padding: "40px 52px", boxSizing: "border-box", transform: `scale(${0.7 + 0.3 * z})`, opacity: z }}>
        <div style={{ fontFamily: MONO, fontSize: 22, color: C.muted, letterSpacing: "0.12em", marginBottom: 12 }}>STEP 2 · WHAT IT DOES WHILE YOU WAIT</div>
        {steps.map((s) => (
          <div key={s.n} style={{ display: "flex", gap: 22, marginTop: 20, alignItems: "flex-start" }}>
            <div style={{ fontFamily: MONO, fontSize: 24, color: C.brand, border: `1px solid ${C.brand}`, borderRadius: 999, width: 44, height: 44, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>{s.n}</div>
            <BlurLine start={s.at} gap={2} dy={22} style={{ fontFamily: SANS, fontSize: 30, color: s.c ?? C.ink, lineHeight: 1.25 }} words={w(s.t)} />
          </div>
        ))}
      </div>
      <Devices />
      <div style={{ opacity: flipIn }}>
        <FlipCard at={196} w={440} h={300} style={{ left: 1255, top: 310 }}
          front={<><div style={{ fontFamily: MONO, fontSize: 20, color: C.muted }}>RUN WITHOUT THE FIX</div><div style={{ fontFamily: SANS, fontSize: 64, fontWeight: 800, color: C.red }}>✗ FAILS</div></>}
          back={<><div style={{ fontFamily: MONO, fontSize: 20, color: C.muted }}>RUN WITH THE FIX</div><div style={{ fontFamily: SANS, fontSize: 64, fontWeight: 800, color: C.green }}>✓ PASSES</div></>} />
      </div>
      {url && <div style={{ position: "absolute", left: 0, right: 0, top: 820, textAlign: "center", fontFamily: MONO, fontSize: 28, color: C.brand, opacity: interpolate(f, [200, 214], [0, 1], clamp) }}>github.com/DesarrolloAntonio/qa-campaign</div>}
    </AbsoluteFill>
  );
};

// What it has found (240f): three real findings from the README. As a hook it opens with a headline.
const Bug = ({ hook }: { hook: boolean }) => {
  const C = useTheme();
  const f = useCurrentFrame();
  const o = (s: number) => interpolate(f, [s, s + 14], [0, 1], clamp);
  const top = hook ? 260 : 220;
  return (
    <AbsoluteFill>
      {hook
        ? <div style={{ position: "absolute", left: 200, top: 90, fontFamily: SANS, color: C.ink }}>
            <BlurLine start={4} gap={3} dy={30} style={{ fontSize: 64, fontWeight: 800, letterSpacing: "-0.02em" }}
              words={[...w("The tests were green. The app was still"), { t: "broken.", c: C.red }]} />
          </div>
        : <div style={{ position: "absolute", left: 200, top: 130, fontFamily: MONO, fontSize: 26, letterSpacing: "0.14em", color: C.muted, opacity: o(0) }}>WHAT IT HAS FOUND</div>}
      <div style={{ position: "absolute", left: 200, top }}><Findings /></div>
      <div style={{ position: "absolute", left: 0, right: 0, top: top + 430, textAlign: "center", fontFamily: SANS, fontSize: 46, fontWeight: 700, color: C.ink, opacity: o(130) }}>
        {hook ? "All found by qa-campaign." : <>All of them in apps whose own tests were <span style={{ color: C.green }}>green</span>.</>}
      </div>
      {!hook && <div style={{ position: "absolute", left: 0, right: 0, top: top + 530, textAlign: "center", fontFamily: MONO, fontSize: 28, color: C.brand, opacity: o(190) }}>github.com/DesarrolloAntonio/qa-campaign</div>}
    </AbsoluteFill>
  );
};

export const Promo: React.FC<Variant> = ({ style, order }) => {
  const hook = order === "bug";
  const scenes: { id: string; dur: number; node: React.ReactNode }[] = [
    { id: "intro", dur: 180, node: <Intro /> },
    { id: "use", dur: 240, node: <><Use /><Caption steps={[{ from: 0, text: "One command in your project" }, { from: 60, text: "It asks first" }, { from: 175, text: "You stay in control" }]} /></> },
    { id: "does", dur: 240, node: <><Does url={hook} /><Caption steps={[{ from: 0, text: "It really uses the app" }, { from: 56, text: "It looks at every screen, at every size" }, { from: 96, text: "It breaks things on purpose" }, { from: 136, text: "It checks what the server stored" }, { from: 176, text: "And proves the fix matters" }]} /></> },
    { id: "bug", dur: 240, node: <><Bug hook={hook} /><Caption steps={[{ from: 0, text: "Real bugs it has found" }, { from: 60, text: "Each one passed the project’s own tests" }, { from: 140, text: "Evidence, not confidence" }]} /></> },
  ];
  // hook order: bug first, then intro, use, does
  const ordered = hook ? [scenes[3], scenes[0], scenes[1], scenes[2]] : scenes;
  let t = 0;
  return (
    <ThemeProvider value={THEMES[style]}>
      <AbsoluteFill>
        <Bg />
        {ordered.map((s) => {
          const from = t;
          t += s.dur;
          return <Sequence key={s.id} from={from} durationInFrames={s.dur}><Fade>{s.node}</Fade></Sequence>;
        })}
      </AbsoluteFill>
    </ThemeProvider>
  );
};

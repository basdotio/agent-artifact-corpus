// "AI yang Pas": one continuous landscape, a keyframed camera that never cuts, captions on top.
// Beat sheet: OneTake/storage/jobs/ai-pas-kurz/beats.md. Every time comes from the voice files through kit's at() and B.
import React, { useMemo } from "react";
import { AbsoluteFill, interpolateColors, useCurrentFrame } from "remotion";
import { rig } from "../../motion";
import { toLines } from "../../Captions";
import { at, B, beatAt, BeatProps, C, CamKey, camTrack, DURATION, FONT, FPS, POP, SHOT, SOFT, WORDS, World } from "./kit";
import { Beat01, Beat02, Beat03, nudgeA } from "./stagesA";
import { Beat04, Beat05, Beat06, nudgeB } from "./stagesB";
import { Beat07, Beat08, Beat09, nudgeC } from "./stagesC";
import { Beat10, Beat11, Beat12, Beat13, nudgeD } from "./stagesD";
import { Beat14, Beat15, nudgeE } from "./stagesE";

export const aiPasDuration = DURATION;
export const aiPasFps = FPS;

const BEATS: React.FC<BeatProps>[] = [Beat01, Beat02, Beat03, Beat04, Beat05, Beat06, Beat07, Beat08, Beat09, Beat10, Beat11, Beat12, Beat13, Beat14, Beat15];
const NUDGES = [nudgeA, nudgeB, nudgeC, nudgeD, nudgeE];

// One move per hand-over, each done before the next beat's first event word.
const KEYS: CamKey[] = [
  { from: 0, to: 0, cam: SHOT[1] },
  // 2: widen from the shore to the sea before the whale breaches on "paus".
  { from: B[2].start - 4, to: at(2, "menyewa") + 6, cam: SHOT[2] },
  // 3: pull back from the whale to the whole landscape.
  { from: at(2, "bukan"), to: B[3].start + 14, cam: SHOT[3] },
  // 4: down to the ant trail, then follow the column right until the perch shows.
  { from: B[4].start, to: B[4].start + 34, cam: SHOT[4] },
  { from: at(4, "semut"), to: at(4, "aturan"), cam: { ...SHOT[4], x: SHOT[4].x + 380 } },
  { from: B[5].start - 4, to: B[5].start + 32, cam: SHOT[5] },
  { from: B[6].start, to: B[6].start + 30, cam: SHOT[6] },
  { from: B[7].start - 4, to: B[7].start + 30, cam: SHOT[7] },
  // 8: drift right to the shore and the sea.
  { from: B[8].start - 6, to: B[8].start + 34, cam: SHOT[8] },
  { from: B[9].start - 6, to: B[9].start + 30, cam: SHOT[9] },
  // 10: down to the bank below the landscape; 11 widens for the second card on "Dinda".
  { from: B[10].start - 4, to: B[10].start + 40, cam: SHOT[10] },
  { from: at(11, "kasnya"), to: at(11, "Dinda") - 4, cam: SHOT[11] },
  // 12–13: back up to the whole landscape, and stay.
  { from: B[12].start - 4, to: at(12, "layar") + 10, cam: SHOT[12] },
  { from: B[14].start - 4, to: B[14].start + 36, cam: SHOT[14] },
  { from: at(14, "Indonesia") + 16, to: B[15].start + 6, cam: SHOT[15] },
];
export const camAt = camTrack(KEYS);

/** Slim caption pill: ink on the card colour, the spoken word eased to gold. */
const SlimCaptions: React.FC<{ frame: number }> = ({ frame }) => {
  const t = frame / FPS;
  const lines = useMemo(() => toLines(WORDS), []);
  const line = lines.find((l) => t >= l[0].start - 0.05 && t <= l[l.length - 1].end + 0.25);
  if (!line) return null;
  const lineIn = rig(frame - Math.round(line[0].start * FPS), FPS, SOFT).v;
  return (
    <div style={{ position: "absolute", bottom: 34, width: "100%", display: "flex", justifyContent: "center", transform: `translateY(${(1 - lineIn) * 12}px)`, opacity: lineIn }}>
      <div style={{
        fontFamily: FONT, fontWeight: 700, fontSize: 30, lineHeight: 1.2, color: C.ink, background: C.card, padding: "7px 22px",
        borderRadius: 999, border: `1.5px solid ${C.line}`, boxShadow: "0 4px 14px rgba(0,0,0,0.35)", maxWidth: 1200, textAlign: "center",
      }}>
        {line.map((w, i) => {
          const on = rig(frame - Math.round(w.start * FPS), FPS, POP).v;
          const off = rig(frame - Math.round((w.end + 0.05) * FPS), FPS, SOFT).v;
          const lit = Math.max(0, Math.min(1, on - off));
          return (
            <span key={i} style={{
              display: "inline-block", marginRight: i < line.length - 1 ? 9 : 0,
              color: interpolateColors(lit, [0, 1], [C.ink, C.gold]), transform: `scale(${1 + 0.04 * (on - off)})`,
            }}>{w.text}</span>
          );
        })}
      </div>
    </div>
  );
};

export const AiPas: React.FC = () => {
  const frame = useCurrentFrame();
  const Beat = BEATS[beatAt(frame) - 1];
  const [nx, ny] = NUDGES.reduce(([x, y], n) => { const [dx, dy] = n(frame); return [x + dx, y + dy]; }, [0, 0]);
  return (
    <AbsoluteFill style={{ background: C.ground, overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `translate(${nx}px, ${ny}px)` }}>
        <World cam={camAt(frame)} fr={frame}>
          <Beat fr={frame} />
        </World>
      </AbsoluteFill>
      <SlimCaptions frame={frame} />
    </AbsoluteFill>
  );
};

// Copy to src/Main.tsx. Arranges scenes in a <Series> (hard cuts, like most
// kinetic-type promos) inside a design-scale wrapper so one set of scenes
// serves both 9:16 and 16:9 compositions (see layout.ts).
import { AbsoluteFill, Series } from "remotion";
import { inter } from "./fonts";
import { SCENES } from "./theme";
import { useLayout } from "./layout";
import { S01Hook } from "./scenes/S01Hook";
// ...import the rest of the scenes

const ORDER: [keyof typeof SCENES, React.FC][] = [
  ["hook", S01Hook],
  // ["reveal", S02Reveal], ...
];

export const Main: React.FC = () => {
  const { W, H, scale } = useLayout();
  return (
    <AbsoluteFill style={{ fontFamily: inter, backgroundColor: "#0A0A0A", overflow: "hidden" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, transform: `scale(${scale})`, transformOrigin: "0 0" }}>
        <Series>
          {ORDER.map(([key, Scene]) => (
            <Series.Sequence key={key} durationInFrames={SCENES[key]} premountFor={15}>
              <Scene />
            </Series.Sequence>
          ))}
        </Series>
      </div>
    </AbsoluteFill>
  );
};

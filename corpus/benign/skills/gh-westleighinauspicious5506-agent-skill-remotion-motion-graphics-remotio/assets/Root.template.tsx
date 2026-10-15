// Copy to src/Root.tsx. Two compositions, same component.
import "./index.css";
import { Composition } from "remotion";
import { Main } from "./Main";
import { LANDSCAPE, PORTRAIT, TOTAL } from "./theme";

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Promo" component={Main} durationInFrames={TOTAL} fps={PORTRAIT.fps} width={PORTRAIT.width} height={PORTRAIT.height} />
    <Composition id="PromoWide" component={Main} durationInFrames={TOTAL} fps={LANDSCAPE.fps} width={LANDSCAPE.width} height={LANDSCAPE.height} />
  </>
);

import { Composition } from "remotion";
import { Promo, TOTAL } from "./Promo";

// Four variants of the same video: style (dark/light) x order (why-first / bug-first).
const variants = [
  { id: "Dark-WhyFirst", style: "dark", order: "why" },
  { id: "Dark-BugFirst", style: "dark", order: "bug" },
  { id: "Light-WhyFirst", style: "light", order: "why" },
  { id: "Light-BugFirst", style: "light", order: "bug" },
] as const;

export const Root = () => (
  <>
    {variants.map((v) => (
      <Composition key={v.id} id={v.id} component={Promo} durationInFrames={TOTAL} fps={30} width={1920} height={1080} defaultProps={{ style: v.style, order: v.order }} />
    ))}
  </>
);

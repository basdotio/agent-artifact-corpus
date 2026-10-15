// Copy to src/fonts.ts. Match the brand's font; Inter is the safe default.
import { loadFont } from "@remotion/google-fonts/Inter";

export const { fontFamily: inter } = loadFont("normal", {
  weights: ["400", "500", "600", "700", "800"],
  subsets: ["latin"],
});

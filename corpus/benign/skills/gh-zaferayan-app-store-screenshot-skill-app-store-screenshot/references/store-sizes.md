# Store Sizes

Use this reference when the user asks for App Store, Google Play, or export sizing.

Store requirements change, so verify current platform requirements when exact compliance matters. When the user does not specify a size, create a high-resolution portrait marketing image that can be resized safely.

## Practical Defaults

Recommended working canvas:

- Portrait: 1290 x 2796 px
- Square/social fallback: 2000 x 2000 px
- Landscape/social fallback: 2400 x 1350 px

Recommended export:

- PNG for final store screenshots, flattened to RGB with no alpha channel. App Store Connect rejects screenshots that contain transparency, and Google Play requires 24-bit PNG (no alpha)
- JPG only when file size matters
- Keep source screenshots and final composites separate when possible

## Apple App Store

Common iPhone portrait screenshot families include:

- 6.9-inch / newer large iPhone class: 1320 x 2868 px or platform-current equivalent
- 6.7-inch class: 1290 x 2796 px
- 6.5-inch class: 1242 x 2688 px or 1284 x 2778 px
- 5.5-inch class: 1242 x 2208 px

App Store Connect accepts 1 to 10 screenshots per device size and scales the largest provided size down for smaller devices, so one 6.9-inch or 6.7-inch set is usually enough.

When the user asks for App Store-ready output, ask for target device sizes only if exact compliance is required. Otherwise, use a large portrait canvas and keep all critical text and phones within safe margins so the composition can be adapted.

## Google Play

Common screenshot constraints:

- JPEG or 24-bit PNG (no alpha)
- Each side between 320 px and 3840 px
- The longer side may be at most 2x the shorter side, so a 1290 x 2796 canvas is too tall. Use 1080 x 1920 or 1440 x 2560 for Play
- 2 to 8 screenshots per device type
- Requirements may vary by device type and policy updates

For phone screenshots, use portrait compositions derived from the source aspect ratio. Keep text large enough for gallery previews and avoid placing critical content at the extreme edges.

## Safe Margins

Keep headlines, device frames, and important details away from edges:

- Minimum margin: 5% of canvas width
- Preferred margin: 7% to 10% of canvas width
- Extra margin near top when using large headlines

Avoid edge-to-edge phone frames unless the user wants an immersive crop for a website hero.

## Multi-Screen Sets

For store galleries:

- Use the same canvas size across every image
- Keep device scale consistent unless intentionally featuring one hero screen
- Keep headline placement consistent
- Use a shared background system with small variations
- Export images in the intended order

Suggested sequence:

1. Core value proposition
2. Main feature
3. Differentiating workflow
4. Trust, insight, or automation
5. Personalization, history, or summary

## Verification Checklist

Before delivering:

- The original screenshot content is unchanged
- The screen is fitted cleanly inside the device frame
- The phone frame does not crop meaningful UI
- The headline is readable at thumbnail size
- The composition has enough safe margin
- The exported dimensions match the requested target or stated default

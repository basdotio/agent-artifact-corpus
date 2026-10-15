# Look guide: what makes it read as clay

These numbers come from the example films. Scale them with the set.

## Motion

- **12 fps, "on twos."** Key every frame with `constant_interp()` so nothing tweens smoothly.
  Smooth interpolation is the #1 tell that it's CG.
- **Boil.** `Boil(seed, amp=0.0002, rot=0.004)` adds about 0.2 mm and 0.2° of random offset per
  frame to each puppet root: the animator's hands touching the clay between shots. Keep it on
  during holds too. Leave the set still.
- **Stepped cycles.** A waddle changes pose every 3 frames (`(f // 3) % 2`), not every frame.
- **Squash and stretch** with roughly constant volume: squash about 12–18% before a hop, stretch
  8–15% in the air, squash again on landing, then settle.
- **Anticipation and settle** around every move, `ease_out_back` for pops, and 4–8 frame holds on
  key poses so the audience can read them.
- **Blinks** are 2 frames. A closed-eye curve replaces the eye bead (swap by scale).
- **Light flicker** of ±1–2% on the key light each frame. Real stop-motion sets flicker.
  Practicals (lanterns, glows) can flicker more (±10%).

## Material (`clay()`)

- Principled BSDF: roughness 0.5–0.7, specular about 0.35, a little subsurface (weight 0.03–0.15,
  scale 0.004 m). Too much SSS reads as wax or gummy candy.
- Surface: low-frequency lumps plus stretched Voronoi edge "thumbprints" in the bump.
  `scale=` sets feature size. Small puppets need a small value (0.13–0.2) so the prints are
  fingertip-sized relative to the object.
- Colour mottling of ±10% value, like kneaded plasticine.
- Geometry `lumpy=` displacement on top, so silhouettes aren't perfect. Rounded boxes always get a bevel.

## Camera and light

- 50 mm lens, f/3–5 for a 5–10 cm puppet at 0.5 m. That gives a miniature depth of field without
  losing the face. The camera stays locked off.
- AgX view transform, "Medium High Contrast" look, exposure −0.45 to −1.0. Clay loses its colour
  and goes pastel as soon as it's overexposed.
- Key: a warm area light, 0.25–0.4 m, from the front left and above. Fill: a cool one, about
  one-tenth the key. Rim: from behind. Add at least one motivated practical: a warm glow in a
  doorway, a desk lamp, or fairy lights out of focus on the back wall.
- Bokeh comes from small emissive spheres (3–8 mm) 0.5–1 m behind the subject.

## Staging

- Build the set as a real tabletop miniature in metres, with a backdrop 0.3–0.6 m behind the action.
- Leave lead room in the direction a character looks or travels. The ending should face camera.
- Contact: compute the lowest point of anything that changes shape (sprouting rays, squashes) so
  it rests on the ground, not through it. `clay_spark.py` shows this.

## Blender API notes (4.2 to 5.x)

- Principled v2 input names are used: `Subsurface Weight`, `Specular IOR Level`, `Coat Weight`.
- 4.4+ layered actions keep F-curves in channel bags. `claylib.all_fcurves()` handles both layouts.
- `bpy.data.textures` `CLOUDS` drives the displace-modifier lumps.
- Render headless with `blender -b -P scene.py -- <args>`. Everything after `--` goes to `cli()`.

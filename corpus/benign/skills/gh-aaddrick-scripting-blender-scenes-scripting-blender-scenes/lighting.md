# Lighting, materials and render

For lights, exposure, colour management, materials, sampling, render passes, interior stills and still cameras. Delivering the file is in `delivery.md`. Read the always-rules in `SKILL.md` first.

**Which parts apply:** every job: rules 1–4, 8 and 12. Reflective materials: 5. Very large subjects: 6. Fog or thin walls: 7. Several shots that must match: 11. Interiors and architecture: the section below.

## Rules

1. **Use realistic light values, and set brightness with Film > Exposure.** Use real units, for example sun 1000 W/m² clear, 500 cloudy, 200 overcast. Renders have no auto-exposure, so correct brightness with Exposure rather than by scaling every light. Ratcheting multipliers between renders is the antipattern: one light went 0.35 → 6.0 → 20.0 in three minutes.
2. **Use AgX (or Khronos PBR Neutral) for final renders, and Standard for data checks.** Filmic is deprecated. A Look changes contrast around middle grey 0.18, so re-measure after changing it.
3. **Measure exposure under the view transform the final render uses.**
   - AgX compresses highlights, so a PNG rarely shows hard clipping. Also check the linear EXR for values above 1.0.
   - Render one frame with the **False Color** view transform. It is a heat map an agent can read: black is low clip, blue through green is mid-tones, red and white are high clip.
   - Measure the clipped and crushed pixel share per region with a script.
4. **Gate material values.**
   - Non-metal albedo is about sRGB 50–240. Never use pure black or white: coal is about 59, fresh snow about 236.
   - Metal base colour is bright, about sRGB 180–250. Darkness comes from roughness and wear, not a dark base colour.
   - Take starting values from physicallybased.info (JSON API at `api.physicallybased.info`). Make the range check a script, not a judgement.
   - Map wear and grime in world space, not object space (see `bpy-pitfalls.md`).
5. **Give reflective materials something to reflect.** Chrome and polished metal in an empty world render black or grey. Add an HDRI or area-light "softboxes", and check the reflection reads in a close-up from the shot camera.
6. **Give scale with cues in the frame, not by faking it.** For a very large subject, use atmospheric haze (Volume Scatter), familiar-size objects (people, vehicles, doors), and a low, wide camera. Heavy depth of field makes a big object read as a miniature.
7. **Judge fog, haze and thin-wall lighting in Cycles.** EEVEE leaks light through thin walls, its volumes are single-scatter only, and they don't show in reflections.
8. **Pin everything that changes the noise.** Set the noise threshold (0.1–0.001), min samples, seed (animated seed off), denoiser and device explicitly. Record the device and denoiser with every render, and compare renders from different devices with a tolerance, not for equality.
9. **Check dim fill lights against the Light Threshold.** It drops light samples that contribute little, so a weak fill light can go noisy or vanish.
10. **Render cheaply while iterating.**
   - Use Workbench or 960×540 Cycles previews, and keep the final tier for a few frames.
   - Benchmark the set-up and confirm the device before any long render: watch `nvidia-smi` during a test frame.
   - Check the Blender build supports your fastest device. A distro package without OptiX cost about 2× on render time until an official build was used.
   - Label every still with the build it came from.
11. **Match adjacent shots by measurement.** Shot-to-shot grading went unsolved in the source production, and the web research found no established recipe, so treat this as a working method rather than proven practice.
    - Measure mean luminance and chromaticity (for example mean a\*/b\* in Lab) on the same regions in each shot: the subject's main surface, a neutral reference surface, and the backdrop. Compare against the neighbouring shots.
    - "Too blue" is a b\* offset you can measure. Find which light or world setting causes it before correcting it.
    - Prefer one shared light rig and one shared grade over per-shot multipliers.
12. **Every lighting change names its neighbours.** An exposure fix that crushes the scale-reference props into black is a regression even when the target metric passes. Report the crushed and clipped share of every region, not just the one you were fixing.

## Interiors and architectural stills

Values verified against Blender 5.2 defaults and the manual. Times of day and lens choices are starting points, not sourced standards.

- **Sun:** `light.energy` is irradiance in W/m² (rule 1). `light.angle` is the disc's angular diameter: the default 0.00918 rad (0.526°) matches the real sun. Raise it for softer shadows. Late afternoon means a low elevation; pick it with the client's reference.
- **Warmth:** (4.5+) `light.use_temperature = True` with `light.temperature` in K (default 6500); `light.color` then acts as a tint. Older builds use a Blackbody node. No source pairs sun elevation with a Kelvin value, so treat warmth as a taste pick against a reference.
- **Sky:** `ShaderNodeTexSky` with `sky_type 'MULTIPLE_SCATTERING'` (5.0+ default; `'SINGLE_SCATTERING'` is the old Nishita). Properties include `sun_elevation`, `sun_rotation`, `altitude`, `air_density`, `aerosol_density` and `ozone_density`. It is very bright by default, so set Exposure. Use either the sky's sun disc (`sun_disc`) or a Sun light, not both.
- **Window light:** put an Area light in each window opening with `light.cycles.is_portal = True`. Portals are invisible and guide world sampling: slower per sample, faster to converge. Use them at openings only, never outdoors. Path guiding (`scene.cycles.use_guiding`, CPU only) is a separate option.
- **Interior vs exterior:** the view through the window is several stops brighter. Set brightness with `scene.cycles.film_exposure` and accept a bright exterior, or composite. Check both regions with the False Color render (rule 3).
- **Glass:**
  - Principled `Transmission Weight` 1, roughness 0, IOR 1.52 for soda-lime glass (physicallybased.info).
  - Window panes block sun and make caustic noise. The manual's fix is a Light Path mix: Glass BSDF for camera rays, Transparent BSDF otherwise. Simpler options are `scene.cycles.caustics_refractive = False`, or `obj.visible_shadow = False` on the pane.
  - Defaults: `max_bounces` 12, `transmission_bounces` 12, `transparent_max_bounces` 8, `glossy_bounces` 4, `diffuse_bounces` 4.
  - Shadow caustics (MNEE) need `light.cycles.is_caustics_light`, `obj.cycles.is_caustics_caster` and `obj.cycles.is_caustics_receiver`. They need smooth normals and ignore bump maps.
- **Noise and fireflies:**
  - Denoise stills with `denoiser 'OPENIMAGEDENOISE'` and `denoising_input_passes 'RGB_ALBEDO_NORMAL'`.
  - `sample_clamp_indirect` defaults to 10 and tames fireflies but dims bright reflections; clamp indirect, not direct.
  - The Light Tree (`use_light_tree`, on by default) ignores custom falloff, ray visibility and textured emission.
- **Straight verticals:** keep the camera level, with `rotation_euler.x = π/2` and no roll, and frame up or down with `camera.data.shift_y` (manual: shift moves the frame without converging verticals). Assert the level camera in the build script. For a 36 mm sensor, 16–24 mm lenses are the usual interior range, and camera height is a judgement call (unverified: no source found for either).

## Red flags

| Thought | Reality |
|---|---|
| "This shot just needs to be warmer" | Measure its chromaticity against the neighbouring shots on the same regions, then find which light causes the shift. |
| "The PNG shows no clipping" | AgX hides it. Check the EXR or the False Color view. |
| "Bump this light ×3 for this shot" | Per-shot multiplier piles become untraceable. Use realistic units and Exposure, and ask why the shot is dark. |
| "Black paint, so base colour 0.0" | Nothing real is below about sRGB 50. Use the value range. |
| "The chrome is metallic 1.0, so it's chrome" | With nothing to reflect it renders flat. Add an environment and look. |
| "Tilt the camera up to fit the ceiling" | Verticals converge. Keep it level and use lens shift. |
| "The room is noisy, so more samples" | Add portals at the windows, and check that the panes aren't blocking the sun. |
| "The EEVEE preview looks right" | Not for fog, haze or thin walls. Check in Cycles. |
| "Same settings, so the renders should match exactly" | Different devices and denoisers differ slightly. Use a tolerance. |

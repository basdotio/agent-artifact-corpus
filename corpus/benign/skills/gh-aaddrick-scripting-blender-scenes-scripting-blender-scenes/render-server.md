# Render-server triage

For a headless render that works on one machine and fails on another: black or missing frames, silent exits, the wrong device. Error-message lookups are in `bpy-pitfalls.md`; checking the delivered file is in `delivery.md`.

When it works on one machine and not another, diff the environments first, then read the log.

1. **Print a fingerprint at the top of every job** and diff it between machines (tested: it reported a planted missing image, and showed the GPU off under `--factory-startup`):
   ```python
   import os, bpy
   def fingerprint():
       sc = bpy.context.scene; cp = bpy.context.preferences.addons['cycles'].preferences
       cp.refresh_devices()
       return dict(blender=bpy.app.version_string, build_hash=bpy.app.build_hash.decode(),
           ocio=os.environ.get("BLENDER_OCIO") or os.environ.get("OCIO"), view=sc.view_settings.view_transform,
           compute_device_type=cp.compute_device_type, devices=[(d.name, d.type, d.use) for d in cp.devices],
           scene_device=sc.cycles.device, denoiser=sc.cycles.use_denoising and sc.cycles.denoiser,
           film_transparent=sc.render.film_transparent,
           output=(sc.render.image_settings.file_format, sc.render.image_settings.color_mode),
           missing_images=sorted(i.filepath for i in bpy.data.images if i.source == 'FILE' and not i.packed_file
                                 and not os.path.exists(bpy.path.abspath(i.filepath))),
           addons=sorted(bpy.context.preferences.addons.keys()))
   ```
   Add `nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used --format=csv` from the shell.
2. **The GPU lives in preferences, not the `.blend`.** A fresh profile or `--factory-startup` gives `compute_device_type 'NONE'`, so `scene.cycles.device = 'GPU'` renders on CPU. Set `cp.compute_device_type` (`'OPTIX'`, `'CUDA'`, `'HIP'` …), call `cp.refresh_devices()`, set `d.use = True`, and assert it in the fingerprint.
3. **Check every frame was written:** each file exists and isn't empty, and none is black. `ffmpeg -framerate 24 -start_number 1 -i f_%04d.png -vf blackdetect=d=0:pix_th=0.10 -an -f null - 2>&1 | grep black_start` works on the image sequence (tested: it found a planted black frame). A count short of the range means the job stopped.
4. **Capture everything:** `blender -b ... --python-exit-code 1 -P job.py --log-level debug --log-file blender.log 2>&1 | tee run.log`, with `set -o pipefail`. Add `--debug-cycles` for device and kernel detail.

| Symptom | Likely causes, and the check |
|---|---|
| Black or empty frames on some shots only | **GPU out of memory:** grep the log for "out of memory"; check `nvidia-smi` for other processes; render frames in separate processes. Whether OOM writes a black frame or fails it is unresolved, so treat both as possible. **Denoiser:** OptiX denoising needs compute capability 7.0+, and OIDN on GPU needs supported hardware (4.1+); re-render with `use_denoising = False`. **Transparent film saved without alpha:** JPEG or RGB shows transparent as black in some viewers. |
| Wrong or magenta textures on the server | Missing files: absolute paths, or `//` paths resolved against a different `.blend` location. See `missing_images` in the fingerprint. |
| Fails on a new driver or card | OptiX needs a recent driver; check the GPU Rendering manual page's minimums for your version. Compare `build_hash` and driver versions. |
| Stops mid-run with exit code 0 | No `--python-exit-code` (or it came after `-P`); a pipe hiding the status; `sys.exit()` or `os._exit()` in a library. The OOM killer sends SIGKILL (137), which a wrapper or pipe can turn into 0: check `dmesg -T \| grep -i "killed process"` or `journalctl -k -g "Out of memory"` (anecdotal: no Blender source). |

## Red flags

| Thought | Reality |
|---|---|
| "The scene says GPU, so it rendered on the GPU" | Device choice lives in preferences. Print the fingerprint and check it. |
| "Exit code 0, so the job finished" | Count the frames written. The flag order, a pipe or a wrapper can all hide a failure. |
| "Same Blender version, so same environment" | Diff the fingerprints: build hash, `OCIO`, devices, denoiser, add-ons, missing files. |

# Field: 3D printing · print-ready models

If research already answered an item, don't ask it — note "confirmed by research" in the summary.
[Recommended defaults] are the first-option candidates.

- **Scale and size**: print scale (1:N), largest printable size, who splits the model into blocks [Recommended: the print shop]
- **Process and material**: FDM / resin / powder; the printer or shop's minimum wall and detail size
- **Minimum thickness**: the threshold at print scale, and how it is measured (parallel-face rays on the evaluated mesh, voxel fill, slicer report)
- **Fixing thin parts**: thicken only the thin direction of the thin members, to just above the threshold [Recommended: minimal, local]
- **Check scope**: geometry only (thickness, closed shell, manifold, self-intersection) / also process (supports, hollowing, drain holes) [Recommended: geometry only]
- **Open details**: trusses, grilles and holes — keep, or turn into closed silhouettes the printer can read
- **Hand-off**: STL / OBJ / 3MF, one file or per part, naming, units in the file
- **Spec sheet**: which numbers go in, which stay out
- [Don't candidates] uniform offset of the whole model, moving every face at the same height, proposing splits or joints, reporting process issues as geometry issues, thickening parts that already pass, fixing by eye without re-measuring

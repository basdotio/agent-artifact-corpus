# SR22T Runway Brief Skill - Changelog

## Version 2.0 - FINAL (2025-10-26)

### Major Changes to Prevent Claude Desktop Rewrites

#### 1. Added `interpolate_performance()` Function
**Problem:** Claude Desktop was rewriting interpolation code, introducing errors.

**Solution:** Created a complete, tested interpolation function in `calculation_functions.py`:
- Handles bilinear interpolation on PA and temperature automatically
- Works for takeoff, landing, and climb gradient data
- Includes automatic rounding (50 ft for distances, 10 ft/NM for gradients)
- Extensively documented with "DO NOT rewrite" warnings

**Usage:**
```python
result = interpolate_performance(
    takeoff_data,
    pressure_altitude,
    actual_temp,
    ['ground_roll_ft', 'total_distance_ft']
)
```

#### 2. Python Standard Filenames
**Problem:** Files with hyphens (`calculation-functions.py`) can't be imported.

**Solution:** Renamed to use underscores:
- `calculation-functions.py` → `calculation_functions.py`
- `sr22t-performance-data.py` → `sr22t_performance_data.py`

Now Claude can use standard Python imports instead of workarounds.

#### 3. Added `__init__.py` for Easy Imports
**Problem:** Claude had to manually add paths and import each function.

**Solution:** Created `references/__init__.py` that exports everything:
```python
from references import EMBEDDED_SR22T_PERFORMANCE, interpolate_performance, ...
```

#### 4. Simplified SKILL.md Code Examples
**Problem:** Long code blocks in SKILL.md encouraged Claude to rewrite.

**Solution:** Replaced 50+ lines of interpolation code with simple function calls:
```python
# OLD: 50 lines of bilinear interpolation code
# NEW: 3 lines using interpolate_performance()
```

#### 5. Enhanced SR22T Flap Logic
**Problem:** Claude was using 50% flaps for crosswinds (wrong for SR22T).

**Solution:**
- Updated SKILL.md with bold header: "SR22T ALWAYS uses 100% flaps"
- Changed logic to ALWAYS set `flap_config = "full_flaps"`
- Crosswind/gust conditions now generate technique notes instead of reducing flaps

#### 6. Stronger Verification Prompt
**Problem:** Claude passed verification then rewrote code anyway.

**Solution:** Created `VERIFICATION-PROMPT.md` with:
- Proof requirements (show actual POH values)
- Function signature confirmation
- Explicit SR22T flap configuration question
- Zero-tolerance policy acknowledgment
- Red flags list (catch common rewrite phrases)

**New verification checks:**
1. Show POH data values to prove it loaded them
2. List all functions WITHOUT rewriting them
3. Show `interpolate_performance()` signature
4. Confirm NO helper functions created
5. Answer: "What flap setting for 15 kt crosswind?" (Must say: 100%)

### Files Changed

**Modified:**
- `SKILL.md` - Simplified to use `interpolate_performance()`, updated imports, fixed flap logic
- `README.md` - Updated file structure diagram with underscored filenames

**Added:**
- `references/__init__.py` - Easy import module
- `references/calculation_functions.py::interpolate_performance()` - Complete interpolation function
- `VERIFICATION-PROMPT.md` - Enhanced verification protocol
- `CHANGELOG.md` - This file

**Renamed:**
- `references/calculation-functions.py` → `references/calculation_functions.py`
- `references/sr22t-performance-data.py` → `references/sr22t_performance_data.py`

### Why These Changes Matter

**Before:**
- Claude rewrote interpolation → introduced calculation errors
- Claude used 50% flaps for crosswinds → wrong for SR22T
- Claude claimed verification passed → then rewrote code anyway
- Files couldn't be imported → forced workarounds

**After:**
- Claude uses `interpolate_performance()` → no rewrites needed
- Claude uses 100% flaps always → correct for SR22T
- Verification catches rewrites → explicit function signature check
- Files can be imported normally → clean Python code

### Safety Impact

✅ **Eliminated the #1 risk:** Claude rewriting safety-critical interpolation code
✅ **Fixed flap configuration:** SR22T-specific logic enforced
✅ **Better verification:** Catches rewrites before they cause problems
✅ **Easier to use:** Standard Python imports = less room for error

### Installation

Use: **`sr22t-runway-brief-FINAL-20251026_131027.zip`** (33.7 KB)

**Steps:**
1. Delete old skill from Claude Desktop
2. Close and restart Claude Desktop
3. Upload new zip file
4. Use VERIFICATION-PROMPT.md before each brief

### Testing Recommendations

After uploading, test with VERIFICATION-PROMPT.md using:
- KBZN runway 30
- Known conditions to verify calculations
- Check that flaps = 100% even with high crosswinds

### Breaking Changes

None - the skill workflow is the same, just safer implementation.

### Credits

- **POH Data:** Cirrus SR22T POH (2023 Revision)
- **Methodology:** Based on v31 Python tool
- **Improvements:** Zero-tolerance for rewrites

---

**Safety Note:** Always use VERIFICATION-PROMPT.md to ensure Claude Desktop is using actual skill code before generating any brief.

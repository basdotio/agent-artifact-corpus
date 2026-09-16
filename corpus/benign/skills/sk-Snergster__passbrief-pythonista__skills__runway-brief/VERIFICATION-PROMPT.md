# SR22T Runway Brief Skill - Verification Prompt

Use this prompt BEFORE requesting any runway brief to verify Claude Desktop is using your actual skill code and data.

---

## Verification Prompt (Copy-Paste This)

```
Before we generate any runway brief, I need you to verify you're using the skill's actual code and data:

MANDATORY VERIFICATION STEPS:

1. PROVE you loaded the actual POH data by showing me:
   - The takeoff ground roll distance at 0 ft PA and 0°C (from EMBEDDED_SR22T_PERFORMANCE)
   - The climb gradient at 0 ft PA and 0°C for 91 KIAS (from EMBEDDED_SR22T_PERFORMANCE)

2. CONFIRM you loaded these functions WITHOUT rewriting them:
   - calculate_pressure_altitude()
   - calculate_isa_temperature()
   - calculate_density_altitude()
   - calculate_wind_components()
   - interpolate_performance()

3. PROVE you will use interpolate_performance() by showing me its function signature:
   - What parameters does it take?
   - What does it return?
   - DO NOT write your own interpolation code

4. STATE your loading method:
   - Did you use: import, exec(), or something else?
   - Did you rewrite ANY functions? (Answer must be NO)
   - Did you write ANY helper functions for interpolation? (Answer must be NO)
   - If you couldn't load the modules, STOP and explain why

5. CONFIRM SR22T flap configuration:
   - What flap setting for landing with 15 kt crosswind?
   - (Correct answer: 100% flaps - SR22T ALWAYS uses full flaps)

6. ACKNOWLEDGE zero-tolerance policy:
   - You will NOT rewrite calculation functions
   - You will NOT create performance data from memory
   - You will NOT write your own interpolation code (use interpolate_performance)
   - You will NOT simplify bilinear interpolation to linear
   - You will NOT approximate or estimate POH values
   - You will NOT reduce flaps for crosswinds (SR22T uses 100% flaps always)
   - If you cannot use my actual code/data, you will STOP immediately

Only after completing this verification may we proceed with the runway brief.
```

---

## Expected Valid Response

Claude Desktop should respond with something like:

```
✓ VERIFICATION COMPLETE

1. POH Data Loaded:
   - Takeoff ground roll at 0 ft PA, 0°C: 1,390 ft (from EMBEDDED_SR22T_PERFORMANCE)
   - Climb gradient at 0 ft PA, 0°C (91 KIAS): 879 ft/NM (from EMBEDDED_SR22T_PERFORMANCE)

2. Functions Loaded:
   ✓ calculate_pressure_altitude() - loaded from skill, NOT rewritten
   ✓ calculate_isa_temperature() - loaded from skill, NOT rewritten
   ✓ calculate_density_altitude() - loaded from skill, NOT rewritten
   ✓ calculate_wind_components() - loaded from skill, NOT rewritten
   ✓ interpolate_performance() - loaded from skill, NOT rewritten

3. interpolate_performance() Function Signature:
   - Parameters: (conditions_list, pressure_altitude, temperature, value_keys)
   - Returns: dict with interpolated values OR single value for climb gradients
   - Handles bilinear interpolation automatically
   - I will NOT write my own interpolation code

4. Loading Method:
   - Used: import or exec() to load references/sr22t_performance_data.py
   - Used: import or exec() to load references/calculation_functions.py
   - Zero functions rewritten - using your exact code
   - Zero helper functions created - using interpolate_performance()

5. SR22T Flap Configuration:
   - Landing with 15 kt crosswind: 100% flaps
   - SR22T ALWAYS uses full flaps for landing (unless flaps inoperative)

6. Zero-Tolerance Policy Acknowledged:
   ✓ Will not rewrite any calculation functions
   ✓ Will not create performance data from memory
   ✓ Will not write my own interpolation code
   ✓ Will not simplify interpolation algorithms
   ✓ Will not approximate POH values
   ✓ Will not reduce flaps for crosswinds
   ✓ Will stop immediately if I cannot use actual skill code/data

Ready to proceed with runway brief.
```

---

## Red Flags (STOP Immediately)

If Claude Desktop says any of these, DO NOT PROCEED:

❌ "I'll use simplified performance data"
❌ "I rewrote the interpolation function to..."
❌ "I created a basic version of..."
❌ "I approximated the POH values..."
❌ "I couldn't load the files so I..."
❌ "Let me fix that..." (followed by rewriting code)
❌ "I'll create helper functions for interpolation"
❌ "I'll use find_bracket_conditions()..." (NOT YOUR FUNCTION)
❌ "I'll use get_performance_value()..." (NOT YOUR FUNCTION)
❌ Shows wrong POH values (e.g., wrong takeoff distance)
❌ Doesn't show the verification data you requested
❌ Says "50% flaps" for crosswind landing
❌ Says it will write "bilinear interpolation" code (use interpolate_performance instead)

---

## Known Correct Values (For Your Reference)

From `EMBEDDED_SR22T_PERFORMANCE`:

**Takeoff Distance (0 ft PA, 0°C):**
- Ground roll: 1,390 ft
- Total to 50 ft: 2,485 ft

**Climb Gradients (0 ft PA, 0°C):**
- 91 KIAS: 879 ft/NM
- 120 KIAS: 768 ft/NM

If Claude shows different numbers, it's using wrong data!

---

## After Successful Verification

Once verified, you can proceed with your actual runway brief request:

```
Generate SR22T runway brief for:
- Airport: KBZN
- Runway: 30
- Elevation: 4,473 ft
- Temperature: 8°C
- Altimeter: 29.88 inHg
- Winds: 230/15G26
- Runway heading: 300° magnetic
- Runway length: 9,000 ft
- Operation: Both (takeoff and landing)
```

---

## Troubleshooting

**If verification fails:**

1. Check that you uploaded `sr22t-runway-brief-FRESH-20251026_123700.zip`
2. Verify the skill shows in Claude Desktop skills list
3. Try deleting and re-uploading the skill
4. Close and restart Claude Desktop
5. Check if the skill files actually have underscores (not hyphens) in the zip

**If Claude keeps rewriting functions:**

- The skill files may not be loading properly
- File paths may be incorrect
- Skill installation may be corrupted
- Report as bug to Claude Desktop

---

**Safety Note:** Never proceed with a runway brief if verification fails. Wrong performance data can cause accidents.

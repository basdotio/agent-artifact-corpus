# Example: Gusty Crosswind Landing

## Scenario

**Location:** KSUN (Friedman Memorial Airport, Sun Valley, Idaho)
**Runway:** 31
**Elevation:** 5,318 ft MSL
**Runway Length:** 7,550 ft
**Runway Heading:** 312° magnetic

**Current Conditions:**
- Temperature: 18°C (cool evening)
- Altimeter: 29.92 inHg (standard)
- Winds: 270/15 gusting 25
- Time: 18:00 local (mountain wave activity)

**Operation:** Landing Brief

---

## Inputs to Skill

```
RUNWAY INFORMATION:
- Runway ID: 31
- Airport Name: KSUN Sun Valley
- Elevation: 5318 ft MSL
- Heading: 312°
- Length: 7550 ft

CURRENT WEATHER:
- Temperature: 18°C
- Altimeter: 29.92
- Wind Direction: 270°
- Wind Speed: 15 kt
- Wind Gusts: 25 kt

OPERATION TYPE: B (Landing Only)
```

---

## Expected Calculations

### Step 1: Common Performance

**Pressure Altitude:**
```
PA = 5318 + (29.92 - 29.92) × 1000
PA = 5318 ft (standard day)
Rounded: 5320 ft
```

**ISA Temperature:**
```
ISA = 15 - (2 × 5.32)
ISA = 15 - 10.64
ISA = 4.4°C
```

**Density Altitude:**
```
DA = 5320 + (120 × (18 - 4.4))
DA = 5320 + (120 × 13.6)
DA = 5320 + 1632
DA = 6952 ft
Rounded: 6950 ft
```

**Assessment:** "Noticeable performance reduction"

**Wind Components:**
```
Wind direction: 270°
Runway heading: 312°
Wind angle = |270 - 312| = 42°

Headwind = 15 × cos(42°) = 15 × 0.743 = 11.1 kt
Crosswind = 15 × sin(42°) = 15 × 0.669 = 10.0 kt

Direction check:
(270 - 312) % 360 = -42 % 360 = 318°
318° is > 270° but not > 90°, so it's from behind-left = tailwind component mixed

Actually, let's recalculate more carefully:
Runway 31 = 312° heading
Wind from 270°

Wind is from left rear quarter of aircraft
Angle from directly behind = 312 - 270 = 42°

Component perpendicular to runway (crosswind) = 15 × sin(42°) = 10.0 kt (left crosswind)
Component along runway:
- Wind from 270° blowing toward 090°
- Runway points 312°
- Wind opposes runway direction?

Let me use proper formula:
angle_diff = (270 - 312) = -42° → normalized to 318°
This is in the range 270° < 318° < 360°, so it's a tailwind

Recalculating with correct understanding:
The wind angle relative to runway is 42°
Headwind component = 15 × cos(42°) = 11.1 kt
But since angle_diff indicates tailwind region, this is actually:
Tailwind = -11.1 kt (approximately)
Crosswind = 10.0 kt left
```

Wait, let me recalculate this properly:

Runway 31 heading = 312°
Wind from 270° (wind blows TO 090°)

Difference: 312° - 270° = 42°

Since runway is 312° and wind is from 270°:
- Wind is from the left rear quarter
- This creates a left crosswind and a tailwind component

Crosswind: 15 × sin(42°) = 10.0 kt
Along-runway component: 15 × cos(42°) = 11.1 kt

But is it headwind or tailwind?
Wind FROM 270° means wind blows TOWARD 090°
Runway 31 points toward 312°
The component of wind along the runway opposes the landing direction → TAILWIND

**Corrected Wind Components:**
- Tailwind: 11.1 kt (unfavorable!)
- Crosswind: 10.0 kt left (moderate)

### Step 2: Flap Configuration

**Gust Factor:**
```
Gust factor = 25 - 15 = 10 kt
```

**Configuration Logic:**
```
Crosswind = 10.0 kt
Gust factor = 10 kt

Is crosswind ≥15 kt? NO
Is crosswind ≥10 kt OR gust factor ≥10 kt? YES (both exactly 10!)

Recommendation: 50% Flaps (Configuration 2)
Reason: "Moderate crosswind (10 kt) and gusty conditions (10 kt gust factor)"
```

**Approach Speeds:**
```
Base final approach (50% flaps) = 87.5 KIAS
Gust correction = 10 × 0.5 = 5 kt
Corrected final approach = 87.5 + 5 = 92.5 KIAS (round to 93 KIAS)

Threshold crossing = 84 KIAS
Touchdown target = 72 KIAS
```

### Step 3: Landing Distance

**Interpolation Bounds:**
- Pressure altitude: Exactly 5000 ft (midpoint available in table)
- Temperature: Between 10°C and 20°C

**Table Values:**
- At PA 5000, Temp 10: Ground roll 1391, Total 2854
- At PA 5000, Temp 20: Ground roll 1440, Total 2930

**Interpolation:**
```
Temp ratio = (18 - 10) / (20 - 10) = 8 / 10 = 0.8

Ground roll = 1391 + 0.8 × (1440 - 1391)
Ground roll = 1391 + 0.8 × 49
Ground roll = 1391 + 39
Ground roll = 1430 ft → 1450 ft (rounded)

Total = 2854 + 0.8 × (2930 - 2854)
Total = 2854 + 0.8 × 76
Total = 2854 + 61
Total = 2915 ft → 2900 ft (rounded)
```

**IMPORTANT NOTE:** This is for full flaps!

**50% Flaps Correction:**
Landing distance with 50% flaps ≈ 110% of full flaps
```
Ground roll (50% flaps) = 1450 × 1.10 = 1595 → 1600 ft
Total (50% flaps) = 2900 × 1.10 = 3190 → 3200 ft
```

**Runway Margin:**
```
Margin = 7550 - 3200 = 4350 ft
Percentage = 4350 / 3200 × 100 = 136%
Assessment: GOOD
```

---

## Expected Output Brief

```markdown
# SR22T LANDING BRIEF - KSUN Sun Valley Runway 31

## PERFORMANCE SUMMARY
**Pressure Altitude:** 5,320 ft (5,318 ft elevation + 0 ft altimeter correction)
**Density Altitude:** 6,950 ft (ISA +13.6°C - Noticeable performance reduction)

**Wind Analysis:**
- Tailwind: 11 kt (UNFAVORABLE)
- Crosswind: 10 kt left (moderate)
- **Gusts:** +10 kt variance (15G25)

## APPROACH CONFIGURATION
**Recommended:** Flaps 50% (Flaps 1)
- **Reason:** Moderate crosswind (10 kt) and gusty conditions (10 kt gust factor)
- Final Approach Speed: 93 KIAS (87.5 base + 5 kt gust correction)
- Threshold Crossing: 84 KIAS
- Touchdown Target: 72 KIAS

**Alternate Configuration (if winds increase):**
- No Flaps: 98 KIAS final (92.5 + 5 kt), 89 KIAS threshold
- Use if crosswind increases above 15 kt

## LANDING PERFORMANCE
**Ground Roll:** 1,600 ft (estimated with 50% flaps)
**Total Distance (over 50ft obstacle):** 3,200 ft (estimated with 50% flaps)

**Runway Analysis:**
- Available: 7,550 ft
- Required: 3,200 ft
- **Margin: 4,350 ft (136% - GOOD)**

## WIND CONSIDERATIONS

⚠️ **TAILWIND CAUTION - 11 kt Component:**
- Tailwind significantly increases landing distance
- Approach will feel faster over ground
- Float tendency increased - resist urge to force landing
- Ground roll will be extended
- **CRITICAL:** Ensure committed to landing early or execute go-around

⚠️ **Gusty Winds (15G25):**
- Extra airspeed carried to flare (+5 kt added to final approach)
- Expect sink on gust lulls during approach
- Maintain firm approach technique
- Use rudder for centerline, aileron into crosswind
- Be ready for go-around if unstabilized below 500 AGL

⚠️ **Moderate Crosswind (10 kt left):**
- Wing-low method recommended
- Lower left wing with aileron, hold centerline with right rudder
- Land on left main wheel first
- Expect drift after touchdown - use rudder/nosewheel steering
- Maintain aileron into wind after touchdown

## GO-AROUND CONSIDERATIONS

**Density Altitude Impact:**
Moderate DA (6,950 ft) reduces climb performance somewhat. Go-around is feasible but plan early:
- Commit to landing or go-around by 300 AGL
- If approach unstable (airspeed ±10 kt, >1 dot deviation, bouncing), GO AROUND
- Do not try to salvage poor approach in gusty tailwind conditions

**Go-Around Technique from 50% Flaps:**
1. Full power immediately
2. Maintain flaps at 50% initially (better climb than full flaps)
3. Positive rate of climb → retract to 0% flaps
4. Climb at Vy (101 KIAS)
5. Consider using Runway 13 (reciprocal) if winds persist

**Runway Environment:**
7,550 ft runway provides adequate safety buffer for go-around decision even midfield. Do not hesitate to execute if approach feels uncomfortable.

## ARRIVAL PASSENGER BRIEF

"We should be landing at Sun Valley in about twelve minutes. Temperature on the ground is eighteen degrees with gusty crosswinds, so you might notice the nose pointed slightly to the left during the approach and a bit of movement—that's completely normal and part of the crosswind landing technique. I'll be talking with the tower and focusing on the approach, so I'll go quiet for a few minutes. Please make sure your seatbelt is tight and anything loose is secured. The approach may feel a little bumpy with these gusts, but the aircraft handles it well."

## SAFETY NOTES

⚠️ **PRIMARY CONCERN: Tailwind Component**
- 11 kt tailwind is significant for mountain runway
- Increases approach speed by ~15-20%
- Float potential high - do not force landing
- Consider requesting Runway 13 (reciprocal) for 11 kt headwind instead

⚠️ **Gusty Crosswind Conditions**
- 10 kt crosswind at limits of moderate technique
- 10 kt gust factor requires extra vigilance
- Combination of tailwind + crosswind + gusts is challenging
- Recommend requesting Runway 13 if pilot not current on crosswind landings

⚠️ **Moderate Density Altitude**
- 6,950 ft DA at 5,318 ft field elevation
- Go-around climb performance reduced ~15%
- Plan go-around early - don't wait until committed

✅ **Adequate Runway Margin**
- 4,350 ft margin provides good safety buffer
- Even with tailwind, runway length is sufficient
- Margin accommodates float from gusts

**GO/NO-GO: ⚠️ GO WITH CAUTION (Recommend Runway 13)**

Current wind conditions (270/15G25) create unfavorable tailwind of 11 kt on Runway 31. While adequate runway margin exists (4,350 ft), the combination of tailwind, moderate crosswind, and gusty conditions presents elevated risk.

**STRONG RECOMMENDATION:** Request Runway 13 (reciprocal), which would provide:
- 11 kt headwind (favorable)
- 10 kt crosswind right (same technique required)
- Significantly reduced landing distance
- Better go-around performance
- Improved safety margins

**If Runway 13 not available or winds favor 31:**
Landing on 31 is feasible but requires proficiency in crosswind technique and acceptance of tailwind limitations. Commit early to landing or go-around. Do not attempt if:
- Pilot not current on crosswind landings (within 90 days)
- Passenger comfort is priority
- Better conditions available by delaying 30-60 minutes
- Any doubt about stabilized approach capability
```

---

## Key Teaching Points

### Why This Example Matters

1. **Tailwind Recognition:**
   - Wind from 270°, runway 312° = 11 kt tailwind component
   - Many pilots miss this and get surprised by float
   - Brief explicitly calculates and warns about tailwind

2. **Configuration Decision:**
   - Crosswind = 10 kt (exactly at threshold)
   - Gust factor = 10 kt (exactly at threshold)
   - Both trigger 50% flaps - demonstrates decision boundary

3. **Runway Request Recommendation:**
   - Brief doesn't just say "GO WITH CAUTION"
   - Provides specific alternative: Use Runway 13
   - Explains why: Tailwind becomes headwind

4. **Passenger Communication for Rough Conditions:**
   - Acknowledges "bit of movement" (normalizes bumps)
   - Explains nose position (crosswind crab/wing-low)
   - Sets expectation without alarming

5. **GO Decision with Conditions:**
   - Not a simple GO or NO-GO
   - "GO WITH CAUTION" + specific recommendation
   - Lists disqualifying conditions (currency, comfort, doubt)

### Common Pilot Errors This Scenario Addresses

**❌ Missing the tailwind:**
- Wind 270°, Runway 31 looks like "crosswind from left"
- Pilots forget to calculate along-runway component
- Result: Surprise float, runway overrun risk

**❌ Using full flaps in gusty crosswinds:**
- "Normal" conditions → full flaps (wrong)
- 10 kt gust factor requires reduced flaps
- Result: Porpoising, hard landing

**❌ Not considering runway reciprocal:**
- "Tower assigned 31, so I have to use 31" (wrong)
- Pilots can request preferred runway for safety
- Brief explicitly recommends asking for 13

**❌ Adding gust correction to touchdown speed:**
- 93 KIAS final approach (correct)
- Trying to touch down at 93 KIAS (wrong)
- Should bleed to ~72 KIAS by touchdown

---

## Decision Tree From This Example

```
Winds 270/15G25 on Runway 31 (heading 312°):

1. Calculate components:
   - Tailwind: 11 kt → UNFAVORABLE
   - Crosswind: 10 kt → MODERATE

2. Check if runway reciprocal available:
   - Runway 13 (heading 132°) would give:
     - Headwind: 11 kt → FAVORABLE
     - Crosswind: 10 kt → MODERATE (same)

3. Decision:
   - Request Runway 13 (better option)
   - If denied, continue with Runway 31 + heightened caution
   - If denied AND not current → consider divert/delay

4. Configuration for Runway 31 (if used):
   - Crosswind 10 kt + Gust factor 10 kt → 50% flaps
   - Final approach: 93 KIAS
   - Expect float, be ready to go around

5. Configuration for Runway 13 (if approved):
   - Crosswind 10 kt + Gust factor 10 kt → 50% flaps
   - Final approach: 93 KIAS
   - Significantly better performance (headwind)
```

---

## Variation: What if Runway 13 Not Available?

**Scenario:** Tower says "Runway 31 only, noise abatement in effect"

**Brief Update:**

```
**GO/NO-GO: ⚠️ GO WITH CAUTION**

Runway 13 not available due to noise abatement. Landing Runway 31 acceptable with following conditions:

**MANDATORY REQUIREMENTS:**
- Pilot current on crosswind landings (within 90 days)
- Stabilized approach criteria strictly enforced
- Go-around decision by 300 AGL (no salvaging poor approach)
- Accept extended float from tailwind (do not force landing)

**TECHNIQUE EMPHASIS:**
- Maintain 93 KIAS on final (do not reduce early)
- Expect to float 500-800 ft down runway
- Land beyond first 2,000 ft acceptable (ample runway remains)
- Full aileron into crosswind after touchdown
- Aggressive braking may be required (tailwind extends ground roll)

**ABORT CRITERIA:**
- Airspeed deviations >±10 kt on final
- Drift >1/2 runway width at 200 AGL
- Approach unstabilized at 500 AGL
- Any sink rate >1000 fpm on gust lull
- Uncomfortable or uncertain feeling about approach

If this is your first tailwind + crosswind + gust combination, consider delaying flight or requesting instructional flight with CFI before solo attempt.
```

---

## Skill Usage Notes

**This example demonstrates:**
- ✅ Correct wind component calculations (including tailwind recognition)
- ✅ Boundary-case configuration decision (10 kt exactly at threshold)
- ✅ Proactive runway recommendation (request reciprocal)
- ✅ Conditional GO decision with specific requirements
- ✅ Passenger brief addressing turbulence appropriately

**Expected skill behavior:**
- Calculate components correctly (tailwind, not headwind)
- Apply flap logic at boundary conditions
- Recommend alternate runway when appropriate
- Provide GO WITH CAUTION (not simple GO/NO-GO)
- List specific abort criteria

**Testing points:**
- Verify tailwind calculation is negative (not positive)
- Confirm 50% flaps selected (not full or none)
- Check passenger brief mentions movement/bumps
- Ensure brief recommends Runway 13 alternative

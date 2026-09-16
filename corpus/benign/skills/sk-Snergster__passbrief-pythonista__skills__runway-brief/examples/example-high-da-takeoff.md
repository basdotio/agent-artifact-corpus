# Example: High Density Altitude Takeoff

## Scenario

**Location:** KEGE (Eagle County Regional Airport, Colorado)
**Runway:** 07
**Elevation:** 6,548 ft MSL
**Runway Length:** 9,000 ft
**Runway Heading:** 070° magnetic

**Current Conditions:**
- Temperature: 32°C (hot summer afternoon)
- Altimeter: 30.15 inHg
- Winds: 090/8 (aligned with runway, slight headwind)
- Time: 15:00 local (hottest part of day)

**Operation:** Takeoff Brief

---

## Inputs to Skill

```
RUNWAY INFORMATION:
- Runway ID: 07
- Airport Name: KEGE Eagle County
- Elevation: 6548 ft MSL
- Heading: 070°
- Length: 9000 ft

CURRENT WEATHER:
- Temperature: 32°C
- Altimeter: 30.15
- Wind Direction: 090°
- Wind Speed: 8 kt
- Wind Gusts: none

OPERATION TYPE: A (Takeoff Only)
```

---

## Expected Calculations

### Step 1: Common Performance

**Pressure Altitude:**
```
PA = 6548 + (29.92 - 30.15) × 1000
PA = 6548 - 230
PA = 6318 ft
Rounded: 6320 ft
```

**ISA Temperature:**
```
ISA = 15 - (2 × 6.32)
ISA = 15 - 12.64
ISA = 2.4°C
```

**Density Altitude:**
```
DA = 6320 + (120 × (32 - 2.4))
DA = 6320 + (120 × 29.6)
DA = 6320 + 3552
DA = 9872 ft
Rounded: 9900 ft
```

**Assessment:** "Significant performance reduction - caution advised"

**Wind Components:**
```
Wind angle = |090 - 070| = 20°
Headwind = 8 × cos(20°) = 8 × 0.94 = 7.5 kt
Crosswind = 8 × sin(20°) = 8 × 0.34 = 2.7 kt
Type: headwind (wind 090, runway 070 - wind from ahead-right)
```

### Step 2: Takeoff Performance

**Interpolation Bounds:**
- Pressure altitude between 6000 ft and 8000 ft
- Temperature between 30°C and 40°C

**Corner Values (from POH table):**
- At PA 6000, Temp 30: Ground roll 2513, Total 3334
- At PA 6000, Temp 40: Ground roll 2694, Total 3561
- At PA 8000, Temp 30: Ground roll 2878, Total 3785
- At PA 8000, Temp 40: Ground roll 3086, Total 4046

**Interpolation:**
- PA ratio: (6320 - 6000) / (8000 - 6000) = 320 / 2000 = 0.16
- Temp ratio: (32 - 30) / (40 - 30) = 2 / 10 = 0.2

**Bottom edge (PA 6000):**
- Ground roll: 2513 + 0.2 × (2694 - 2513) = 2513 + 36 = 2549
- Total: 3334 + 0.2 × (3561 - 3334) = 3334 + 45 = 3379

**Top edge (PA 8000):**
- Ground roll: 2878 + 0.2 × (3086 - 2878) = 2878 + 42 = 2920
- Total: 3785 + 0.2 × (4046 - 3785) = 3785 + 52 = 3837

**Final interpolation:**
- Ground roll: 2549 + 0.16 × (2920 - 2549) = 2549 + 59 = 2608 ft → **2600 ft**
- Total: 3379 + 0.16 × (3837 - 3379) = 3379 + 73 = 3452 ft → **3450 ft**

**Runway Margin:**
```
Margin = 9000 - 3450 = 5550 ft
Percentage = 5550 / 3450 × 100 = 161%
Assessment: EXCELLENT
```

### Step 3: Climb Gradient

Using climb gradient table at 91 KIAS, interpolating for density altitude 9900 ft:

**Corner values:**
- At PA 8000, Temp 40: 468 ft/NM
- At PA 10000, Temp 40: 431 ft/NM

Interpolation: ~450 ft/NM at 91 KIAS

### Step 4: CAPS Altitudes

```
CAPS Minimum MSL = 6548 + 600 = 7148 ft MSL
CAPS Recommended MSL = 6548 + 2000 = 8548 ft MSL
Pattern Altitude MSL = 6548 + 1000 = 7548 ft MSL
```

---

## Expected Output Brief

```markdown
# SR22T TAKEOFF BRIEF - KEGE Eagle County Runway 07

## PERFORMANCE SUMMARY
**Pressure Altitude:** 6,320 ft (6,548 ft elevation - 230 ft altimeter correction)
**Density Altitude:** 9,900 ft (ISA +29.6°C - Significant performance reduction)

**Wind Analysis:**
- Headwind: 7.5 kt (favorable)
- Crosswind: 2.7 kt (light)

## TAKEOFF PERFORMANCE
**Ground Roll:** 2,600 ft
**Total Distance to 50ft:** 3,450 ft

**Runway Analysis:**
- Available: 9,000 ft
- Required: 3,450 ft
- **Margin: 5,550 ft (161% - EXCELLENT)**

## CLIMB PERFORMANCE
**At 91 KIAS (Initial Climb):**
- Climb Gradient: 450 ft/NM
- Estimated Rate: ~900 fpm at 100 kt groundspeed

**At 120 KIAS (Enroute Climb):**
- Climb Gradient: 350 ft/NM
- Estimated Rate: ~710 fpm at 130 kt groundspeed

## CAPS ALTITUDES
**Field Elevation:** 6,548 ft MSL
**CAPS Minimum:** 7,148 ft MSL (600 ft AGL) - Emergency deployment only
**CAPS Recommended:** 8,548 ft MSL (2,000 ft AGL) - Optimal deployment window
**Pattern Altitude:** 7,548 ft MSL (1,000 ft AGL) - CAPS fully effective

## EMERGENCY BRIEF - Phased Approach

**Phase 1 (Ground Roll - 0 to rotation):**
If engine failure occurs before rotation: **ABORT TAKEOFF** - Close throttle, apply brakes, stop on remaining runway (6,400 ft available).

**Phase 2 (Rotation to 7,148 ft MSL):**
If engine failure: Land straight ahead or within 30° of runway heading. Insufficient altitude for CAPS deployment.

**Phase 3 (7,148 ft to 8,548 ft MSL):**
If engine failure: **IMMEDIATE CAPS DEPLOYMENT** - Pull red handle without hesitation. Limited time for successful deployment at these altitudes.

**Phase 4 (Above 8,548 ft MSL):**
If engine failure: Troubleshoot per POH checklist. CAPS available if unable to resolve. Time permits decision-making.

## DEPARTURE PASSENGER BRIEF

"Here's what to expect for our takeoff from Eagle County: We're taking off from a high-elevation mountain airport at about 6,500 feet, and with the warm temperatures today, you'll notice a longer takeoff roll and climb than you might be used to at sea level—this is completely normal for mountain operations. With today's headwind helping us out, we have plenty of runway and excellent margins. This Cirrus is equipped with the CAPS whole-plane parachute system for an extra layer of safety. Keep your seatbelt snug as we climb to our cruising altitude, and enjoy the spectacular mountain views!"

## SAFETY NOTES

⚠️ **High Density Altitude** (9,900 ft):
- Performance reduced approximately 35% compared to sea level
- Extended takeoff roll - expect to use 2,600 ft before rotation
- Reduced climb performance - shallow climb angle initially
- Engine may feel less responsive than at lower elevations

✅ **Excellent Runway Margin**:
- 5,550 ft margin provides ample safety buffer
- Headwind component further improves performance
- Abort capability maintained through most of takeoff roll

✅ **Favorable Winds**:
- 7.5 kt headwind reduces takeoff distance by ~10-12%
- Light crosswind (2.7 kt) requires minimal technique
- Winds aligned with runway - no significant gusts reported

⚠️ **Mountain Environment Considerations**:
- Terrain rises rapidly after departure - maintain best angle climb (91 KIAS) until well clear
- Be aware of updrafts/downdrafts typical of afternoon mountain flying
- Density altitude will increase as temperature rises through afternoon
- Consider morning departure for better performance if flexible

**GO/NO-GO: ✅ GO**

Excellent runway margin (161%) provides safe operation despite high density altitude. Headwind component and ample runway length more than compensate for reduced performance. Recommend maintaining heightened awareness of terrain clearance during climbout and strict adherence to best angle climb speed until clear of obstacles. If this is your first high-altitude departure, the extended takeoff roll and reduced climb rate are normal - resist urge to rotate early.
```

---

## Key Teaching Points

### Why This Example Matters

1. **High Density Altitude Reality:**
   - DA of 9,900 ft at field elevation of 6,548 ft
   - ISA deviation of +29.6°C (very hot day)
   - Performance degradation of ~35%
   - Demonstrates importance of runway margin

2. **Margin Adequacy:**
   - Despite poor performance, excellent margins maintained
   - 5,550 ft margin = 161% safety buffer
   - Demonstrates how long runways compensate for high DA

3. **Passenger Communication:**
   - Brief specifically mentions longer takeoff roll
   - Sets expectation for normal mountain operations
   - Reduces passenger anxiety about extended ground roll

4. **CAPS Integration:**
   - At 6,548 ft field elevation, CAPS minimum is 7,148 ft MSL
   - Only 600 ft AGL to work with initially
   - Phase 2 (before CAPS minimum) is very short
   - Emphasizes importance of maintaining best angle climb

5. **GO Decision:**
   - Despite high DA warning, brief concludes GO
   - Reasoning: Excellent margin overcomes performance degradation
   - Conditional: Maintain best angle climb for terrain clearance
   - Educational note for first-time mountain flyers

### Variations to Test

**Same scenario, but:**
- Runway length: 6,000 ft → Margin drops to 2,550 ft (74% - still GOOD, but tighter)
- Temperature: 38°C → DA increases to 10,620 ft, distances increase further
- Winds: Calm → Lose headwind advantage, margins tighten
- Afternoon thunderstorms building → May warrant NO-GO despite adequate margins

### Common Pilot Errors This Scenario Addresses

**❌ Rotating too early:**
- High DA = less lift at given airspeed
- Early rotation = settling back to runway or mush climb
- Brief emphasizes extended ground roll is normal

**❌ Climbing at too high airspeed:**
- Vx (best angle) critical for terrain clearance
- Vy (best rate) would result in slower altitude gain over distance
- Brief specifically recommends 91 KIAS until clear of terrain

**❌ Underestimating DA impact:**
- 35% performance reduction is significant
- Without briefing, pilot might think airplane is broken
- Brief sets expectations and explains why it's normal

---

## Comparison: Same Airport, Morning Conditions

**If same flight at 07:00 local with temp 15°C:**

**Density Altitude:**
```
ISA at PA 6320 = 2.4°C
DA = 6320 + (120 × (15 - 2.4))
DA = 6320 + 1512
DA = 7832 ft → 7850 ft
```

**Performance Improvement:**
- Takeoff distance reduces by ~400 ft
- Climb gradient improves by ~80 ft/NM
- Margin increases from 5,550 to ~5,950 ft

**Decision Impact:**
- Morning departure: EXCELLENT conditions, routine operation
- Afternoon departure: Still GO, but with heightened awareness
- This is why mountain pilots prefer morning departures

---

## Skill Usage Notes

**This example demonstrates:**
- ✅ Proper high-DA warnings
- ✅ GO decision despite marginal performance (due to excellent margin)
- ✅ Passenger brief acknowledging conditions
- ✅ Specific technique recommendations (Vx for terrain)
- ✅ Educational notes for learning pilots

**Expected skill behavior:**
- Flag high DA prominently
- Calculate accurate distances using interpolation
- Assess margins correctly (EXCELLENT despite conditions)
- Generate appropriate passenger brief
- Provide conditional GO (maintain Vx, terrain awareness)

# SR22T V-Speeds and Configuration Reference

## Overview

This guide explains V-speed selection logic, flap configurations, and wind corrections for SR22T approach and landing operations.

---

## Approach Speed Configurations

### Configuration 1: Full Flaps (100%)

**When to use:**
- Crosswind <10 kt
- No significant gusts (<10 kt gust factor)
- Normal landing conditions

**Speeds:**
- Final Approach: **82.5 KIAS** (base speed)
- Threshold Crossing: **79 KIAS**
- Touchdown Target: **67 KIAS** (just above stall)

**Advantages:**
- Shortest landing distance
- Best forward visibility over nose
- Steeper approach angle (better obstacle clearance)
- Most common configuration

**Disadvantages:**
- More susceptible to crosswind drift
- Greater float tendency in gusts
- Less go-around performance

---

### Configuration 2: Partial Flaps (50% / Flaps 1)

**When to use:**
- Crosswind 10-15 kt
- Gusty conditions (gust factor ≥10 kt)
- Recommended for most non-standard conditions

**Speeds:**
- Final Approach: **87.5 KIAS** (base speed)
- Threshold Crossing: **84 KIAS**
- Touchdown Target: **72 KIAS**

**Advantages:**
- Better crosswind control authority
- Less float in gusty conditions
- Improved go-around climb performance
- More stable in turbulence

**Disadvantages:**
- Slightly longer landing distance (~10%)
- Faster touchdown speed
- Flatter approach angle

---

### Configuration 3: No Flaps

**When to use:**
- Crosswind >15 kt
- Very gusty conditions (>20 kt gusts)
- Emergency situations
- Flap system malfunction

**Speeds:**
- Final Approach: **92.5 KIAS** (base speed)
- Threshold Crossing: **89 KIAS**
- Touchdown Target: **77 KIAS**

**Advantages:**
- Maximum control authority
- Best go-around performance
- Most stable in severe turbulence
- Least drift in crosswinds

**Disadvantages:**
- Longest landing distance (~30% more than full flaps)
- Fastest touchdown speed
- Flattest approach (requires more runway for obstacle clearance)
- Hardest to judge landing flare

---

## Configuration Selection Decision Tree

```
1. Is crosswind ≥15 kt?
   YES → Use No Flaps (Configuration 3)
   NO → Continue to 2

2. Is crosswind ≥10 kt OR gust factor ≥10 kt?
   YES → Use 50% Flaps (Configuration 2)
   NO → Continue to 3

3. Normal conditions
   → Use Full Flaps (Configuration 1)
```

### Gust Factor Calculation

**Gust Factor = Peak Gust Speed - Sustained Wind Speed**

**Examples:**
- Winds 15G25 → Gust factor = 25 - 15 = 10 kt
- Winds 12G18 → Gust factor = 18 - 12 = 6 kt
- Winds 20G30 → Gust factor = 30 - 20 = 10 kt

**Interpretation:**
- <5 kt gust factor: Light gusts, minimal impact
- 5-10 kt gust factor: Moderate gusts, consider 50% flaps
- ≥10 kt gust factor: Significant gusts, use 50% flaps
- >15 kt gust factor: Severe gusts, consider no flaps

---

## Gust Corrections

### Add Half the Gust Factor to Approach Speed

**Formula:**
```
Gust Correction = Gust Factor × 0.5
Final Approach Speed = Base Speed + Gust Correction
```

**Examples:**

**Example 1: Winds 15G25 with Full Flaps**
- Gust factor = 25 - 15 = 10 kt
- Gust correction = 10 × 0.5 = 5 kt
- Base final approach (full flaps) = 82.5 KIAS
- **Corrected final approach = 82.5 + 5 = 87.5 KIAS**

**Example 2: Winds 12G18 with 50% Flaps**
- Gust factor = 18 - 12 = 6 kt
- Gust correction = 6 × 0.5 = 3 kt
- Base final approach (50% flaps) = 87.5 KIAS
- **Corrected final approach = 87.5 + 3 = 90.5 KIAS** (round to 91 KIAS)

**Example 3: Calm Winds (10 kt, no gusts)**
- Gust factor = 0 kt
- Gust correction = 0 kt
- Base final approach = 82.5 KIAS
- **Final approach = 82.5 KIAS** (no correction needed)

### Important Notes

**Do NOT add gust correction to:**
- Threshold crossing speed
- Touchdown target speed

**Why:** The extra speed is carried on approach to handle gust-induced airspeed variations. As you enter the flare, you bleed off the extra energy. Touchdown should still be at the normal target speed (or slightly faster due to residual energy).

**Technique:**
- Maintain corrected speed until approximately 100 ft AGL
- Begin flare, allow speed to decay naturally
- Target normal touchdown speed, accepting 2-3 kt faster if gusts persist

---

## Weight Corrections

**Performance data assumes max gross weight (3,600 lb).**

### Speed Reduction for Lighter Weight

**Formula:**
```
Speed Reduction = (Max Gross - Actual Weight) / 100
Final Speed = Base Speed - Speed Reduction
```

**Example:**
- Max gross weight: 3,600 lb
- Actual weight: 3,400 lb
- Weight difference: 3,600 - 3,400 = 200 lb
- Speed reduction: 200 / 100 = 2 kt
- Base final approach (full flaps): 82.5 KIAS
- **Corrected for weight: 82.5 - 2 = 80.5 KIAS**

**When to apply:**
- Significant weight reduction (>100 lb under max gross)
- Not needed for typical flights (most SR22T operations near max gross)

**Do NOT combine with gust corrections if gusts present:**
- Gust correction takes priority
- Flying slower than base speed in gusts is dangerous

---

## Crosswind Technique

### Light Crosswind (<10 kt) with Full Flaps

**Technique: Crab on Final, Kick on Flare**
1. Crab into wind on final approach
2. Maintain runway centerline
3. Just before flare, use rudder to align fuselage with runway
4. Apply aileron into wind to prevent drift
5. Land on upwind main wheel first

**Common Errors:**
- Insufficient rudder in flare (land in crab)
- Too much aileron (scrape wingtip)
- Late correction (drift off centerline)

### Moderate Crosswind (10-15 kt) with 50% Flaps

**Technique: Wing-Low Method**
1. Crab on approach initially
2. Transition to wing-low method on short final
3. Lower upwind wing with aileron
4. Apply opposite rudder to maintain centerline
5. Land on upwind main wheel
6. Progressively lower downwind wheel

**Advantages over crab-and-kick:**
- More stable in gusts
- Better directional control
- Easier to maintain crosswind correction after touchdown

### Strong Crosswind (>15 kt) with No Flaps

**Technique: Wing-Low Throughout**
1. Use wing-low method from final approach
2. More aggressive aileron deflection needed
3. Significant rudder to hold centerline
4. Higher approach speed (92.5 KIAS base)
5. Firm touchdown on upwind wheel
6. Immediate full aileron into wind after touchdown

**Critical Notes:**
- Maximum demonstrated crosswind for SR22T: 21 kt
- If crosswind >15 kt, strongly consider alternate runway
- Gusty crosswinds >20 kt: Landing not recommended

---

## Decision Criteria

### When to Use Alternate Runway

**Consider alternate if:**
- Crosswind component >15 kt
- Gust factor >15 kt
- Tailwind component >5 kt
- Combination of moderate crosswind (10 kt) + gusts (10 kt)

**Decision Example:**
Winds 270/20G30, Runway 09 (heading 090°)

**Analysis:**
- Wind 180° off runway heading = direct tailwind
- Tailwind component = 20 kt (unacceptable)
- **Decision: Use Runway 27** (becomes 20 kt headwind)

### When to Delay Landing

**Delay if:**
- Windshear reported
- Severe gusts with rapid direction changes
- Crosswind at personal proficiency limits
- Inadequate runway margin for configuration required

**Example:**
Crosswind 16 kt on 5,000 ft runway, DA 8,000 ft

**Analysis:**
- Crosswind requires no-flap configuration
- No-flap landing distance significantly longer
- High DA further degrades performance
- Runway margin may be inadequate
- **Decision: Wait for winds to decrease or divert**

---

## Configuration Impact on Landing Distance

**Relative Landing Distance (Approximate):**
- Full Flaps: 100% (baseline)
- 50% Flaps: 110% (+10%)
- No Flaps: 130% (+30%)

**Example:**
- Full flap distance at PA 4000, Temp 20°C: 2,848 ft
- 50% flap distance (estimated): ~3,130 ft (+282 ft)
- No flap distance (estimated): ~3,700 ft (+852 ft)

**Important:** POH tables are for full flaps only. Partial/no flap distances are estimates. Add conserv margin.

---

## Quick Reference Card

### Configuration Selection

| Condition | Crosswind | Gusts | Config | Base Speed |
|-----------|-----------|-------|--------|------------|
| Normal | <10 kt | <10 kt | Full Flaps | 82.5 KIAS |
| Moderate Wind | 10-15 kt | OR ≥10 kt | 50% Flaps | 87.5 KIAS |
| Strong Wind | >15 kt | OR >15 kt | No Flaps | 92.5 KIAS |

### Gust Correction

```
Gust Correction = (Peak Gust - Sustained) × 0.5
Add correction to final approach speed only
Do NOT add to threshold or touchdown speeds
```

### Go-Around From Each Config

| Config | Best Action | Notes |
|--------|-------------|-------|
| Full Flaps | Retract to 50% immediately | Full power, climb at Vx (79 KIAS) |
| 50% Flaps | Maintain or retract to 0% | Climb at Vy (101 KIAS) |
| No Flaps | Maintain clean config | Best climb performance |

---

## Common Mistakes to Avoid

**❌ Using full flaps in gusty conditions**
- Results in porpoising, ballooning, hard landings
- Use 50% flaps when gust factor ≥10 kt

**❌ Not adding gust correction**
- Flying base speed in gusts risks stall on gust lull
- Always add half the gust factor

**❌ Adding gust correction to touchdown speed**
- Lands too fast, extends ground roll significantly
- Bleed speed in flare to normal touchdown target

**❌ Using no-flap when not needed**
- Wastes runway unnecessarily
- Harder to judge flare
- Only use for crosswind >15 kt or emergency

**❌ Ignoring weight corrections**
- Not critical for typical operations
- Matters for very light weight (<3,400 lb)

---

## Summary

**Key Principles:**
1. Match configuration to wind conditions
2. Add half gust factor to approach speed
3. DO NOT add gust correction to touchdown speed
4. Consider alternate runway for strong crosswinds
5. Delay landing if conditions exceed proficiency

**Priority Order:**
1. Safety first - never exceed personal limits
2. Use most restrictive configuration (when in doubt, use less flaps)
3. Have go-around plan ready before every landing
4. Brief configuration and speeds before pattern entry

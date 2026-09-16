# SR22T Runway Brief Skill

Quick takeoff and landing performance calculator for Cirrus SR22T operations at any runway worldwide.

## Overview

This Claude Skill provides rapid, accurate performance analysis for SR22T runway operations without requiring full flight planning tools. Perfect for:

- Quick feasibility checks at unfamiliar airports
- Hot/cold day performance verification
- Backcountry strip analysis
- Return flight margin checks after weather changes
- Training scenarios and what-if calculations

## What This Skill Provides

**Takeoff Brief:**
- Pressure and density altitude calculations
- Wind component analysis
- Takeoff distance and runway margin
- Climb gradients (91 KIAS and 120 KIAS)
- CAPS deployment altitudes
- Phased emergency procedures
- Departure passenger briefing script
- GO/NO-GO decision with reasoning

**Landing Brief:**
- Pressure and density altitude calculations
- Wind component analysis
- Flap configuration recommendation
- Approach speeds with gust corrections
- Landing distance and runway margin
- Wind technique guidance
- Go-around considerations
- Arrival passenger briefing script
- GO/NO-GO decision with reasoning

## Quick Start

### Required Inputs (7 items):

1. Runway elevation (feet MSL)
2. Current temperature (°C)
3. Current altimeter (inHg)
4. Wind direction (degrees magnetic)
5. Wind speed (knots)
6. Runway heading (degrees magnetic)
7. Runway length (feet)

**Optional:** Wind gusts, Operation type

### Example Usage in Claude

```
Using the SR22T Runway Brief skill:

Runway: 09 at KSUN (Sun Valley, 5,318 ft elevation)
Temperature: 28°C
Altimeter: 30.12
Winds: 120/8
Runway heading: 092° magnetic
Runway length: 7,550 ft
Operation: Takeoff
```

Claude will provide a complete brief in ~30 seconds.

## File Structure

```
runway-brief/
├── SKILL.md                          # Main skill workflow
├── README.md                         # This file
├── references/
│   ├── sr22t_performance_data.py    # Complete POH tables
│   ├── calculation_functions.py     # All formulas with tests
│   └── v-speeds-reference.md        # Configuration selection guide
└── examples/
    ├── example-high-da-takeoff.md   # Mountain airport scenario
    └── example-crosswind-landing.md # Gusty conditions scenario
```

## Installation

### For Claude Desktop (when Skills launch)

1. Zip this directory:
   ```bash
   cd skills
   zip -r runway-brief.zip runway-brief/
   ```

2. Upload to Claude → Settings → Skills → Add Skill

3. Select skill type:
   - **Personal:** Available across all your projects
   - **Project:** Scoped to current project only

### For ChatGPT/Gemini (manual attachment)

1. Create .zip as above
2. Attach to conversation
3. Invoke with: "Using the SR22T Runway Brief skill attached, [your inputs]"

## Usage Examples

### Example 1: Quick Takeoff Check

**Scenario:** Standing at unfamiliar backcountry strip, need to know if you can depart safely.

**Input:**
```
Runway 24, elevation 6,200 ft
Temp 32°C, Altimeter 29.85, Winds 240/12
Runway length 4,500 ft
Takeoff brief only
```

**Output:** Complete brief with:
- Density altitude: 9,450 ft (high DA warning)
- Takeoff distance: 3,200 ft
- Runway margin: 1,300 ft (29% - ADEQUATE)
- GO WITH CAUTION decision + specific recommendations

**Time:** ~30 seconds vs 5+ minutes with full tool

---

### Example 2: Hot Day Return Check

**Scenario:** Flew into mountain airport in cool morning. Now 15:00, temps climbed. Can you still land safely?

**Input:**
```
Runway 09, elevation 5,500 ft
Temp 35°C (was 18°C this morning)
Altimeter 30.10, Winds 110/15 gusting 22
Runway length 6,000 ft
Landing brief
```

**Output:** Complete brief with:
- Density altitude: 9,200 ft (vs 6,800 ft this morning)
- Landing config: 50% flaps (gusts)
- Landing distance: 3,400 ft
- Margin: 2,600 ft (76% - GOOD)
- GO decision but recommends waiting for cooler temps if flexible

---

### Example 3: Both Operations (Round-Trip Analysis)

**Input:**
```
Operation: Both
[Same inputs as above]
```

**Output:** Both briefs PLUS comparative analysis:
- Takeoff margin: 2,100 ft (47%)
- Landing margin: 2,600 ft (76%)
- Most restrictive: Takeoff
- Recommendation: Depart now (cooler), return later (hotter but still adequate)

---

## Skill Features

### Automatic Safety Logic

**GO/NO-GO Categories:**
- **NO-GO:** Margin <0 ft (required > available)
- **GO WITH CAUTION:** Margin 0-25%
- **GO:** Margin >25%

**Automatic Warnings:**
- High density altitude (>8,000 ft)
- Crosswinds (10+ kt moderate, 15+ kt strong)
- Gusty conditions (10+ kt gust factor)
- Tailwind component (any amount flagged)
- Short runways (<3,000 ft)

### Configuration Logic

**Landing flap selection:**
- Full flaps: Crosswind <10 kt, gusts <10 kt
- 50% flaps: Crosswind 10-15 kt OR gusts ≥10 kt
- No flaps: Crosswind >15 kt

**Gust corrections:**
- Adds half the gust factor to approach speed
- Applied to final approach only (not touchdown)

### Passenger Briefing

**Departure brief includes:**
- Flight context and weather tone
- CAPS safety system mention (mandatory)
- Specific passenger preparation

**Arrival brief includes:**
- Time to landing estimate
- Sterile cockpit explanation (mandatory)
- Seatbelt and loose items reminder

---

## Validation & Testing

### Calculation Accuracy

All formulas tested against known values:
- ✅ Pressure altitude calculations
- ✅ Density altitude formulas
- ✅ Wind component trigonometry
- ✅ Bilinear interpolation

See `references/calculation_functions.py` for test cases.

### Performance Data Source

- **Aircraft:** Cirrus SR22T
- **Weight:** 3,600 lb (max gross)
- **Source:** 2023 Cirrus SR22T POH
- **Tables:** Takeoff distance, landing distance, climb gradients

### Consistency Testing

Run same inputs multiple times - outputs should be identical (±0 ft variance on rounded values).

**Test case:**
```
PA 4000 ft, Temp 25°C, Calm winds
Expected: Takeoff distance 2,748 ft (every run)
```

---

## Limitations

**This skill does NOT:**
- ❌ Fetch live weather (you input ATIS/METAR data)
- ❌ Parse Garmin Pilot briefings
- ❌ Analyze route weather (TFRs, SIGMETs)
- ❌ Calculate fuel requirements
- ❌ Perform weight & balance
- ❌ Provide magnetic variation (you provide magnetic headings)

**This skill DOES:**
- ✅ Calculate performance accurately from POH data
- ✅ Assess runway margins with GO/NO-GO guidance
- ✅ Recommend flap configurations for conditions
- ✅ Generate passenger briefing scripts
- ✅ Provide technique guidance for winds

---

## Troubleshooting

### "Output varies between runs"

**Problem:** Getting different distances for same inputs
**Solution:** Check that you're using exact Python code from `references/calculation_functions.py`. Don't let Claude approximate - use provided interpolation algorithms.

### "Flap configuration seems wrong"

**Problem:** Full flaps recommended when crosswind is 12 kt
**Solution:** Check gust factor. If gusts <10 kt and crosswind <15 kt, full flaps may be correct. See `references/v-speeds-reference.md` for decision tree.

### "Passenger brief missing CAPS mention"

**Problem:** Departure brief doesn't mention CAPS
**Solution:** This is a validation failure. CAPS mention is mandatory for every departure brief. Re-run with validation checklist.

### "Margins seem too optimistic"

**Problem:** Skill says GO but you're uncomfortable
**Solution:** Skill uses POH data for max gross weight. If lighter, actual performance will be better. But if density altitude is very high, consider the GO WITH CAUTION guidance seriously.

---

## Advanced Usage

### Scenario Planning

Use skill to test multiple scenarios:

```
Scenario A: Current conditions (32°C, winds 15G22)
Scenario B: Wait 2 hours (28°C estimated, winds calm)
Scenario C: Depart opposite runway (headwind vs tailwind)

Compare margins and make informed decision
```

### Training Tool

Instructors can use skill to:
- Demonstrate high-DA impact (same airport, vary temperature)
- Show crosswind configuration logic (vary wind angle)
- Teach runway margin assessment (vary runway length)

### Pre-Buy Evaluation

Considering buying into SR22T partnership?
- Test typical airports you'd fly to
- Verify performance meets mission needs
- Understand hot-day limitations

---

## Future Enhancements (Not in v1.0)

**Potential additions:**
- Multi-aircraft support (SR22, SR20, other models)
- Weight & balance integration
- Short-field technique recommendations
- Contaminated runway adjustments (wet, snow)
- Metric unit support

**Feedback welcome:** Open an issue on GitHub

---

## Safety Notes

**CRITICAL AVIATION SAFETY:**

This skill uses certified POH performance data, but YOU are the pilot in command:

1. **Cross-check calculations** - Verify critical numbers match POH
2. **Conservative margins** - Add personal minimums beyond skill's GO/NO-GO
3. **Current proficiency** - GO decision assumes proficiency in technique
4. **Weather changes** - Conditions can change between brief and operation
5. **Emergency plan** - Always have abort/go-around plan

**The skill provides data. YOU make the final decision.**

**In case of doubt:** Delay departure, request alternate runway, or divert. No schedule is worth compromising safety.

---

## Version History

**v1.0.0** (2025-01-20)
- Initial release
- Takeoff and landing brief workflows
- Complete POH data tables
- Passenger briefing generation
- Examples for high-DA and crosswind scenarios

---

## Credits

**Aircraft Data:** Cirrus SR22T POH (2023 Revision)
**License:** MIT

---

## Support

**Questions or Issues:**
- Check examples/ directory for similar scenarios
- Review references/ files for calculation details

**Bug Reports:**
- Include: inputs used, expected output, actual output
- Specify which validation check failed

---

## Quick Reference Card

### Input Checklist
- [ ] Runway elevation (ft MSL)
- [ ] Temperature (°C)
- [ ] Altimeter (inHg)
- [ ] Wind direction (° magnetic)
- [ ] Wind speed (kt)
- [ ] Runway heading (° magnetic)
- [ ] Runway length (ft)

### Output Includes
- [ ] Pressure/density altitude
- [ ] Wind components
- [ ] Performance distances
- [ ] Runway margin assessment
- [ ] Passenger brief script
- [ ] GO/NO-GO decision
- [ ] Safety notes and warnings

### Typical Usage Time
- Input gathering: 10-15 seconds (read ATIS, check chart)
- Brief generation: 20-30 seconds
- **Total: <1 minute**

---

**Ready to use!** Invoke the skill with your runway and weather data.

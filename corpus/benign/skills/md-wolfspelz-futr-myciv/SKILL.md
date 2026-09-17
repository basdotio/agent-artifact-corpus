---
name: myciv
description: Interactive research session to add a new civilization to FUTR
argument-hint: [civilization-spec]
---

# Add Civilization - Interactive Research Session

Research and add a new civilization (polity at a point in time) to the FUTR database.

**IMPORTANT: At the start of every session, read `.claude/rules/content.md` for YAML schemas, directory structure, naming conventions, and image policies.**

## Input
The user provides a **civilization specification** - a hint at universe, polity, and time frame.
Examples: "Andorians from Star Trek at Federation founding", "Galactic Empire at fall of Coruscant"

## Workflow

### Step 1: Identifying
1. **Read `.claude/rules/content.md`** for schemas and structural conventions
2. Research the specification online to verify it's unambiguous
3. Identify: Universe, Polity, Civilization name, Date
4. Check if the universe/polity already exists in `data/universes/`
5. Ask clarifying questions if the specification is ambiguous
6. Ask the user which language all texts (readme fields, descriptions, image captions) should be written in (e.g., English or German)
7. Confirm the identified civilization and language with the user

### Step 2: General Research
1. Search for descriptive and metric data about the civilization
2. Find material on: population, territory, technology, government, military, culture
3. Check existing metrics in `data/metrics/` that could apply
4. Propose new metrics if needed (ask user)
5. Present findings and ask which metrics to include

### Step 3: Metrics Research
1. Research specific values for each selected metric
2. Determine confidence levels
3. Find min/max ranges where uncertain
   - **Canon/semiCanon values**: Consider whether min/max are needed. If the value is exact and certain, omit min and max. If the source gives an approximate or rounded number (e.g., "about 50,000 worlds"), estimate plausible min/max ranges, since canon does not always mean precise. Official media (official maps, TV shows, movies, published novels, studio-sanctioned material) is always `canon`, not `semiCanon`. Use `semiCanon` only for secondary sources (RPG sourcebooks, technical manuals, creator interviews, decanonized material).
4. **Cross-check values against existing data** (e.g., compare Kardashev to Earth 2023 = 0.73 and other civilizations, but also show other comparisons of other metrics) -- these comparisons are for validation only, do not include them in readme fields
5. **In-universe comparisons**: When sources compare to places that share real-world names (e.g., "Sol System", "Earth", "Mars"), assume they refer to the in-universe version at the same time period, not real-world data. Research the in-universe reference to properly contextualize the comparison.
6. Gather reference URLs for all values

### Step 4: Review
1. Present all proposed data in tables:
   - New metrics (if any)
   - Polity info
   - Civilization info
   - **Datapoints table with comparisons** (see format below)
2. Ask user to approve or adjust values
3. Iterate until user is satisfied

**Datapoints Comparison Table Format:**
For EVERY datapoint, show comparable values from existing civilizations to help maintain consistency.
Include a short **Rationale** column summarizing why the value was chosen (key source, calculation method, or reasoning):

| Metric | Value | Min | Max | Confidence | Rationale | Comparisons (same universe) | Comparisons (other universes) |
|--------|-------|-------|-------|------------|-----------|----------------------------|-------------------------------|
| Population | - | 8e9 | - | canon | Wiki states ~8 billion | Empire 2040: 25e9 | Earth 2023: 8e9, Federation 2373: 1e12 |
| Kardashev | 0.82 | 0.85 | 0.87 | calculated | 8e9 x 20kW/person = 1.6e14 W | Empire 2040: 1.2 | Earth 2023: 0.73, Federation 2373: 2.1 |
| Planets | 12 | - | - | canon | Source lists 12 colonies | Empire 2040: 150 | Federation 2373: 150 |

- Query existing civilizations in `data/universes/` for comparison data
- Prioritize comparisons from the same universe first
- Include Earth 2023 as baseline reference where applicable
- These comparisons are for validation only -- do NOT include them in readme fields or files

**Kardashev Calculation Rationale (REQUIRED):**
For every Kardashev value, show the calculation rationale including per-person power consumption:

1. **Calculate total power**: Estimate civilization's total energy consumption in Watts
2. **Calculate per-person power**: Total power / Population = Watts per person
3. **Compare to Earth 2023 baseline**: Earth uses ~18 TW for 8.1e9 people = ~2,200 W/person
4. **Apply Kardashev formula**: K = log10(Power) / 10 - 0.6 (where Power is in Watts)
   - Type I = 10^16 W (~1.2e6 W/person for 8e9 people)
   - Type II = 10^26 W (full stellar output)
5. **Show the math**: Present the calculation transparently so it can be verified

Example rationale:
```
Population: 50e12, Estimated power: 10^24 W
Per-person: 10^24 / 50e12 = 2e10 W/person (vs Earth 2023: 2,200 W/person = 9 million x more)
Kardashev: log10(10^24) / 10 - 0.6 = 24/10 - 0.6 = 1.8
```

### Step 5: Image Research & Attribution (REQUIRED)
1. Find images (see content.md for approved sources and proxy instructions)
   - **Try to find 5 images for each item** (universe, polity, civilization). Search broadly: presskits, promotional material, key art, official wallpapers, concept art, production stills, poster art, maps, logos/emblems, key characters, ships/technology, book/media covers, battle scenes, cities/locations, flags/symbols, screenshots, fan art Creative Commons, etc.
2. **For EVERY image, research and document all attribution fields:**
   - `src`: Direct image URL (or `/proxy/...` path for proxied images)
   - `text`: Caption/description for the image
   - `link`: Source page URL for attribution (e.g., Wikimedia Commons file page, publisher page)
   - `author`: Creator/artist name (search for the artist, e.g., book cover artists, map creators)
   - `license`: Short identifier (e.g., "CC BY-SA 4.0", "Public Domain", "(c) Publisher" for copyrighted works)
   - `legal`: Full license text or URL (e.g., "https://creativecommons.org/licenses/by-sa/4.0/" or "Copyrighted by [Publisher]. Used for commentary under Fair Use.")
3. **Image description strategy (minimize image scanning):**
   - **Always prefer metadata over scanning**: Use the image's alt attribute, filename, surrounding page text, caption, title attribute, or Wikimedia Commons file description to determine what the image shows
   - Only scan or visually interpret an image if no textual metadata is available to describe it
4. **Research strategy for attribution:**
   - Wikimedia Commons: Fetch the file page to find author and license info
   - Book covers: Search for "[book title] cover artist" - publishers like Baen often use known artists
   - Fan wiki images: Check the file page for upload info and licensing
   - Official art: Note the copyright holder (studio, publisher) and use Fair Use rationale
5. **Proxy images from Wikimedia/Wikipedia** (see content.md Image Proxy section) before proceeding to selection
6. **Use the Image Selector tool** to let the user visually pick images:
   - Pipe the candidate images as a JSON array directly into the selector (do NOT create temp files):
     `echo '<json array>' | python tools/imageselector/imageselector.py`
   - Each object must have `src`, `text`, `link`, `author`, `license`, `legal`, and optionally `tags`
   - For `/proxy/` images, ensure the files are downloaded to `data/proxy/` first so the tool can display them
   - The tool opens a GUI grid showing all candidates. The user clicks to select/deselect, and drags to reorder. The first image becomes the tile/primary image.
   - Parse the JSON output (stdout) as the final selected images. The output order matches the user's chosen order — use it directly for the `images:` list in info.yaml.
   - If the tool exits with code 1, the user cancelled -- ask what they'd like to change
7. **Only include images with complete attribution** in the image selector. If attribution is incomplete (missing author, license, or legal), do not add the image to the candidate list. Skip it silently or search for a better-attributed alternative.
8. Write descriptions for polity and civilization readme fields
9. Gather links to official/wiki pages

### Step 6: Implementation
1. Create directories and info.yaml files following schemas in content.md:
   - `data/universes/{Universe}/info.yaml` (if new universe -- include `tags: [index, new]`)
   - `data/metrics/{NewMetric}/info.yaml` (if new metrics)
   - `data/universes/{Universe}/_polities/{Polity}/info.yaml` (if new polity)
   - `data/universes/{Universe}/{Civilization}/info.yaml` (include `tags: [index, new]`)
   - `data/universes/{Universe}/{Civilization}/{Metric}/info.yaml` (datapoints)
2. **Update `showcaseMetrics` in Universe info.yaml** (REQUIRED):
   - Check which metrics have datapoints across multiple civilizations in this universe
   - Update `showcaseMetrics` list to include all metrics that enable comparisons
   - Example: `showcaseMetrics: [Population, Kardashev, Planets, Star Systems, Warships]`
3. **Add `sources` to Universe info.yaml** (REQUIRED for new universes, update for existing):
   - Add a `sources` key listing ALL URLs that were valuable during research
   - Include every link that contained useful information, contributed to content generation, or informed metric values
   - Organize with comments by category (primary, wiki, Kardashev estimates, forums, etc.)
   - These are not displayed on the site but serve as a reference for future research in the same universe
   - Example:
     ```yaml
     sources:
       # Primary
       - https://official-wiki.example.com/Main  # population, territory, governance
       # Fan wikis
       - https://fandom.example.com/wiki/Topic  # war losses data
       # Kardashev estimates
       - https://kardashev.fandom.com/wiki/Civ  # Type II classification
       # Forums
       - https://forums.example.com/thread/123  # ship count estimates
     ```
4. Verify all files created
5. Check if `.claude/settings.local.json` was modified (new permissions added during research)
6. Commit all changes together (data files + settings if modified) with message: "add {Civilization} civilization"

## Writing Style
- **All descriptions and readme texts MUST be written in present tense** (historisches Prasens / historical present), regardless of language. Example: "Das Imperium umfasst 50.000 Welten" (not "umfasste"), "The Empire controls 150 worlds" (not "controlled").
- **Use em dashes (Gedankenstrich) rarely**. Prefer commas, periods, or restructured sentences.
- **In-universe perspective**: Write all descriptions (universe, polity, civilization readmes) from an in-universe point of view, as if recorded by an accomplished historian within that universe. No publishing details, no meta-references to books, episodes, or authors. Focus on events, peoples, politics, and technology as historical facts.
- **Readme/description length**: Descriptions must be at least 1/4 page and at most 1 page long (roughly 75-300 words).
- Write in the language confirmed with the user in Step 1. (Of course keep all YAML keywords in English.)
- **After writing all readme texts, use the `humanizer` skill to refine them** before including them in YAML files.

## Finding New Universes
When looking for civilizations to add, these lists are good starting points:
- https://en.wikipedia.org/wiki/List_of_science_fiction_universes
- https://en.wikipedia.org/wiki/Category:Science_fiction_franchises

## Research Sources (by priority)
1. **Official sources** - Creator-sanctioned content (Memory Alpha, Wookieepedia verified)
2. **Fan wikis** - Memory Alpha, Wookieepedia, various fandom wikis
3. **Wikipedia universe lists** - Check if the universe appears on https://en.wikipedia.org/wiki/List_of_science_fiction_universes or https://en.wikipedia.org/wiki/Category:Science_fiction_franchises for overview info and cross-references
4. **TV Tropes** - tvtropes.org for trope classification, scale comparisons (especially https://tvtropes.org/pmwiki/pmwiki.php/JustForFun/AbusingTheKardashevScaleForFunAndProfit for Kardashev analysis), and cross-universe references. Search via `https://tvtropes.org/pmwiki/search_result.php#gsc.tab=0&gsc.q=<query>` replacing `<query>` with the search term.
5. **Atomic Rockets** - projectrho.com for hard-science worldbuilding data, formulas, and tech classification. Search via `https://www.google.com/search?q=<query>&sitesearch=projectrho.com%2Fpublic_html%2Frocket` replacing `<query>` with the search term.
6. **Original works** - Books, shows, movies, games
7. **Scholarly analysis** - Academic papers on fictional universes
8. **Fan calculations** - Well-reasoned community estimates

## TV Tropes Reference Pages by Metric

When researching a civilization, check these TV Tropes pages for cross-universe comparisons and community-sourced data. Start with the universe page, then check metric-specific pages.

### Universe Pages (start here)
All FUTR-tracked universes have dedicated pages:
- Star Trek: https://tvtropes.org/pmwiki/pmwiki.php/Franchise/StarTrek
- Star Wars: https://tvtropes.org/pmwiki/pmwiki.php/Franchise/StarWars
- Warhammer 40K: https://tvtropes.org/pmwiki/pmwiki.php/Franchise/Warhammer40000
- Halo: https://tvtropes.org/pmwiki/pmwiki.php/Franchise/Halo
- Honorverse: https://tvtropes.org/pmwiki/pmwiki.php/Literature/HonorHarrington
- The Culture: https://tvtropes.org/pmwiki/pmwiki.php/Literature/TheCulture
- Orion's Arm: https://tvtropes.org/pmwiki/pmwiki.php/Website/OrionsArm
- Perry Rhodan: https://tvtropes.org/pmwiki/pmwiki.php/Literature/PerryRhodan
- Stellaris: https://tvtropes.org/pmwiki/pmwiki.php/VideoGame/Stellaris
- Traveller: https://tvtropes.org/pmwiki/pmwiki.php/TabletopGame/Traveller

### Kardashev
- https://tvtropes.org/pmwiki/pmwiki.php/JustForFun/AbusingTheKardashevScaleForFunAndProfit — hundreds of civilizations pre-categorized Type 0 through IV+ with wattage thresholds
- https://tvtropes.org/pmwiki/pmwiki.php/Main/DysonSphere — civilizations with Dyson spheres (instant Type II+ indicator)
- https://tvtropes.org/pmwiki/pmwiki.php/Main/RingWorldPlanet — megastructure builders

### Techlevel / Tech Summary
- https://tvtropes.org/pmwiki/pmwiki.php/Main/TechnologyLevels — franchise-specific tech tier systems (e.g. Halo's 7-tier Forerunner scale)
- https://tvtropes.org/pmwiki/pmwiki.php/Main/HigherTechSpecies — relative tech rankings within a universe
- https://tvtropes.org/pmwiki/pmwiki.php/SlidingScale/MohsScaleOfScienceFictionHardness — how "hard" a universe's science is (calibrates tech claims)
- https://tvtropes.org/pmwiki/pmwiki.php/Main/SchizoTech — civilizations with inconsistent tech levels
- https://tvtropes.org/pmwiki/pmwiki.php/Main/LostTechnology — post-collapse civilizations with degraded tech

### Class
- https://tvtropes.org/pmwiki/pmwiki.php/Main/GalacticSuperpower — galaxy-spanning polities (Class 15+)
- https://tvtropes.org/pmwiki/pmwiki.php/Main/SufficientlyAdvancedAlien — godlike civilizations (highest Class)
- https://tvtropes.org/pmwiki/pmwiki.php/Main/VestigialEmpire — declining civilizations with shrinking reach
- https://tvtropes.org/pmwiki/pmwiki.php/Main/StandardSciFiHistory — civilization development stages

### Population
- https://tvtropes.org/pmwiki/pmwiki.php/Main/AbsurdlyHugePopulation — fiction's population numbers with franchise examples
- https://tvtropes.org/pmwiki/pmwiki.php/Main/CityPlanet — ecumenopolis population data (Coruscant, Trantor)
- https://tvtropes.org/pmwiki/pmwiki.php/Main/SciFiWritersHaveNoSenseOfScale — flags implausible numbers, useful for sanity checks

### Planets / Star Systems / Territory
- https://tvtropes.org/pmwiki/pmwiki.php/Main/GalacticSuperpower — territory and planet counts for major empires
- https://tvtropes.org/pmwiki/pmwiki.php/Main/SpaceSector — how fiction divides territory into sectors
- https://tvtropes.org/pmwiki/pmwiki.php/Main/ColonizedSolarSystem — single-system civilizations

### FTL
- https://tvtropes.org/pmwiki/pmwiki.php/Main/FasterThanLightTravel — master page categorizing FTL methods
- https://tvtropes.org/pmwiki/pmwiki.php/Main/FasterThanLightIndex — index of all FTL-related tropes
- https://tvtropes.org/pmwiki/pmwiki.php/Main/SubspaceOrHyperspace — specific FTL implementations per franchise

### Government
- https://tvtropes.org/pmwiki/pmwiki.php/Main/TheEmpire — militaristic expansionist empires
- https://tvtropes.org/pmwiki/pmwiki.php/Main/TheFederation — democratic multi-species unions
- https://tvtropes.org/pmwiki/pmwiki.php/Main/HegemonicEmpire — soft-power empires

### Warships
- https://tvtropes.org/pmwiki/pmwiki.php/Main/StandardSciFiFleet — fleet composition tropes
- https://tvtropes.org/pmwiki/pmwiki.php/Main/SpaceNavy — military space forces

### Civilization Age
- https://tvtropes.org/pmwiki/pmwiki.php/Main/Precursors — ancient advanced civilizations and their capabilities
- https://tvtropes.org/pmwiki/pmwiki.php/Main/TheCycleOfEmpires — rise/peak/decline patterns, helps identify snapshot timing

## Atomic Rockets Reference Pages by Metric

Hard-science worldbuilding reference with formulas, calculations, and tech classification systems. Base URL: `https://www.projectrho.com/public_html/rocket/`

### Kardashev
- `techlevel.php` — Kardashev scale definitions, Traveller RPG TLs, linear vs branched tech trees
- `location.php` — megastructures (ringworlds, pocket universes, Big Dumb Objects)
- `alientech.php` — apes-or-angels spectrum, probability of tech gaps between civilizations

### Techlevel / Tech Summary
- `techlevel.php` — core tech level discussion, franchise-specific tier systems (Traveller, Star Hero)
- `scisociety4.php` — divergent tech paths (green/bio vs gray/mechanical, Shaper/Mechanist)
- `engineintro.php` — Drive Table comparing all engine types by performance (chemical through antimatter)
- `fasterlight.php` + `fasterlight2.php` — FTL drive classification with 3 formal taxonomies (Landis, EMF, Peetes Com)

### Class
- `techlevel.php` — Kardashev and Traveller scales as class proxies
- `stellarempire.php` — empire typologies (Stross, Eisler, Pournelle axes), governance models
- `futurehistory.php` — 9 civilization development stages (solar exploration through transcendence)
- `alientech.php` — forerunner civilizations, Clarke's apes-or-angels framework

### Population
- `empiremap.php` — star density formula (N = R^3 * 0.017), habitable planet formula (N = R^3 * 0.0022)
- `stellarcolony.php` — population growth models (Malthusian exponential, logistic)
- `spacecolony.php` — habitat capacities (O'Neill: 25K-2M, Cole bubbles: up to 10M)
- `modelhistory.php` — mathematical civilization projections (Barnes model, HANDY collapse model)

### Planets / Star Systems / Territory
- `empiremap.php` — star count formulas by radius, expansion rate models, colonization economics
- `colonysite.php` — habitable planet density per cubic light-year
- `planetroles.php` — planet function taxonomy (Capital, Factory, Farm, Military, Mine, Gate, Penal)
- `telecommunication.php` — how communication speed constrains maximum empire size

### FTL
- `fasterlight.php` — FTL physics, causality violations, warp vs jump classification
- `fasterlight2.php` — 3 classification taxonomies: Landis (discontinuous/continuous), EMF (Type 0-III+X), Peetes Com (2x2 matrix)
- `telecommunication.php` — FTL comms framework (2x2: FTL travel yes/no x FTL comms yes/no)

### Government
- `stellarempire.php` — historical empire models mapped to SF (Aztec, Mongol, British trade, etc.)
- `empiredyn.php` — empire rise/fall dynamics, energy-shift instability theory
- `telecommunication.php` — comms speed determines centralization vs autonomy

### Warships
- `astromilitary.php` — fleet organization hierarchy (Task Element through Fleet), ship classification
- `spacewarship.php` — warship design types (laserstar, kinetistar, carrier, lancer, patrol)
- `spacewar.php` — warfare motivations, strategic considerations

### Civilization Age
- `futurehistory.php` — 9-stage development framework
- `modelhistory.php` — mathematical timeline projections (8 tech surges over 300 years)
- `empiredyn.php` — empire duration data, rise/fall cycle patterns

## Common Metrics to Research
For any civilization, try to find data on:
1. Population (total, and breakdown by type if available)
2. Kardashev level (energy usage, technological capability)
3. Class (unified 1-20 scale) and Tech Summary (short text description)
4. Number of inhabited planets/worlds
5. Territory size (if measurable) and Location
6. Age of civilization
7. Key dates (founding, major events)

## Shell Pitfalls
- **Never use brace expansion inside double quotes.** `mkdir -p "path/{A,B,C}"` creates a single literal directory named `{A,B,C}`. Use separate `mkdir -p` calls or unquoted brace expansion instead.

## Quality Checks
- All datapoints MUST have references
- Cross-check Kardashev against Earth 2023 (K=0.73) for sanity
- Use existing metrics when possible before creating new ones
- **Always update `showcaseMetrics`** in universe info.yaml to include all metrics with datapoints
- Images should be from canonical/official sources when available
- **All images MUST have complete attribution** (see content.md for required fields and approved sources)
- **New universes and civilizations MUST have `tags: [index, new]`**
- **All info.yaml files MUST have `created` and `changed` dates** (see content.md Timestamps)

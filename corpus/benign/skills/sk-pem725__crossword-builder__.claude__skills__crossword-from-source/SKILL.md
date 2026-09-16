---
name: crossword-from-source
description: Generate educational crossword puzzles by extracting vocabulary from source files. Use when users want to create crossword puzzles from lecture notes, textbook content, documentation, or code files. Triggers on requests like "create a crossword from this file", "make a vocabulary puzzle from my notes", or "generate a crossword for my students". Designed for college-level students with moderate verbal fluency (SAT-level, not GRE).
---

# Crossword Puzzle Generator

Generate crossword puzzles from source material for educational use.

## Process

### 1. Gather Source Material

Ask which files to analyze if not specified. Accept text, markdown, PDF, or code files.

### 2. Extract Key Terms

Identify 15-25 meaningful terms:

**Include:** Technical terminology, proper nouns, domain vocabulary, words appearing multiple times
**Exclude:** Common words, words <4 or >15 letters, obscure jargon

### 3. Generate Clues

Create clues at college level with moderate verbal fluency. See [references/clue-guidelines.md](references/clue-guidelines.md) for detailed calibration.

**Distribution:** 60% straightforward, 30% moderate, 10% challenging

**Clue types:**
- Definitional: "Process of cell division producing gametes" → MEIOSIS
- Contextual: "In the reading, this structure stores genetic information" → NUCLEUS
- Fill-in-blank: "The ___ principle states position and momentum cannot both be precisely known" → UNCERTAINTY

### 4. Generate Grid

Create a valid crossword grid:
- Size 15x15 for 15-20 words, scale as needed
- Use rotational symmetry (180-degree)
- All words must intersect; no isolated sections
- Minimum 4-letter words

Use `src/crossword/grid_generator.py` if available, or generate algorithmically.

### 5. Output

Provide puzzle in this structure:

```
## [PUZZLE TITLE]

### Grid (Student Version)
[ASCII grid with numbers, empty squares]

### Clues
**ACROSS**
1. [Clue] (N letters)

**DOWN**
1. [Clue] (N letters)

---
### Answer Key
[Filled grid]
```

See [references/output-formats.md](references/output-formats.md) for ASCII rendering and JSON export format.

### 6. Render Output Files

After generating the grid and clues, render the puzzle to publishable formats:

```python
from src.crossword import render_all

files = render_all(puzzle, "output/", basename="week03_vocab",
                   title="Week 3: Motivation", subtitle="PSYC 405")
# files → {"png": "...", "png_key": "...", "pdf": "...", "html": "..."}
```

- **PNG** — printable grid image (student + answer key)
- **PDF** — full worksheet with header, grid, two-column clues, and answer key page
- **HTML** — self-contained interactive puzzle (no CDN, works offline, hostable anywhere)

## Options

- **Difficulty level**: Adjust clue subtlety (easy/medium/hard)
- **Word count**: Target specific number of terms
- **Theme**: Focus on specific topics from source
- **JSON export**: Provide structured data for web rendering
- **Output format**: Choose `html`, `pdf`, `png`, or `all` (default: `all`)

# Output Formats

## ASCII Grid Rendering

### Characters

| Character | Meaning |
|-----------|---------|
| `███` | Blocked/black square |
| `[ ]` | Empty letter cell (student version) |
| `[A]` | Filled letter (answer key) |
| Numbers | Word start positions |

### Student Grid Example

```
███│ 1 │ 2 │███│███│ 3 │███
───┼───┼───┼───┼───┼───┼───
 4 │   │   │   │   │   │███
───┼───┼───┼───┼───┼───┼───
███│   │███│ 5 │   │   │
───┼───┼───┼───┼───┼───┼───
 6 │   │   │   │███│   │███
```

### Answer Key Example

```
███│ 1P│ 2Y│███│███│ 3L│███
───┼───┼───┼───┼───┼───┼───
 4C│  O│  T│  H│  O│  N│███
───┼───┼───┼───┼───┼───┼───
███│  D│███│ 5A│  R│  R│  Y
───┼───┼───┼───┼───┼───┼───
 6D│  E│  A│  D│███│  A│███
```

## JSON Export Format

For web integration, provide structured JSON:

```json
{
  "title": "Chapter 5 Vocabulary",
  "size": {
    "rows": 15,
    "cols": 15
  },
  "grid": [
    [".", "P", "Y", ".", ".", "L", "."],
    ["C", "O", "T", "H", "O", "N", "."],
    [".", "D", ".", "A", "R", "R", "Y"],
    ["D", "E", "A", "D", ".", "A", "."]
  ],
  "clues": {
    "across": [
      {
        "number": 4,
        "clue": "Popular programming language named after a comedy troupe",
        "answer": "PYTHON",
        "row": 1,
        "col": 0,
        "length": 6
      }
    ],
    "down": [
      {
        "number": 1,
        "clue": "Function without a name",
        "answer": "POD",
        "row": 0,
        "col": 1,
        "length": 3
      }
    ]
  }
}
```

### JSON Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Puzzle title |
| `size.rows` | int | Grid height |
| `size.cols` | int | Grid width |
| `grid` | string[][] | 2D array, "." for blocked |
| `clues.across` | array | Across clue objects |
| `clues.down` | array | Down clue objects |

### Clue Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `number` | int | Clue number |
| `clue` | string | Clue text |
| `answer` | string | Answer (uppercase) |
| `row` | int | Starting row (0-indexed) |
| `col` | int | Starting column (0-indexed) |
| `length` | int | Word length |

## PNG Rendering

Generated via `render("png", ...)` or `render_all()`. Uses Pillow.

| Property | Default |
|----------|---------|
| DPI | 300 (print quality) |
| Cell size | 40 px |
| Blocked cells | Black fill |
| Numbers | Top-left corner, grey |
| Fonts | Helvetica → Arial → DejaVu → Pillow default |

`render_png_pair()` produces both student (blank) and answer-key versions.

## PDF Worksheet

Generated via `render("pdf", ...)` or `render_all()`. Uses fpdf2.

**Page 1:**
1. Header: title, subtitle, name/date fields
2. Instructions line
3. Embedded grid PNG (student version)
4. Two-column clue list (Across | Down)

**Page 2:** Answer key grid (optional, on by default).

## Interactive HTML

Generated via `render("html", ...)` or `render_all()`. No extra dependencies.

**Self-contained** single file — no CDN links, works offline, hostable anywhere.

| Feature | Description |
|---------|-------------|
| Cell navigation | Click cells, arrow keys |
| Letter input | Type directly into cells |
| Clue highlight | Click clue to highlight its word in grid |
| Direction toggle | Click same cell to switch Across ↔ Down |
| Check | Red/green feedback (2 s flash) |
| Reveal Word | Fills current word with answers |
| Clear All | Resets all entered letters |
| Progress save | Automatic via localStorage |
| Print fallback | `@media print` CSS strips interactive styling |
| Responsive | Side-by-side on desktop, stacked on mobile |

Puzzle data is embedded as JSON in a `<script>` tag (same structure as JSON Export above).

## Print-Ready Format

For classroom handouts, include:

1. **Header**: Title, date, instructions
2. **Grid**: Student version with clear numbering
3. **Clues**: Two-column layout (Across | Down)
4. **Footer**: Point value or time limit if applicable

Separate answer key on different page for instructor use.

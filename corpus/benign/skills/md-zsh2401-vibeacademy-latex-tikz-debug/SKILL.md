---
name: latex-tikz-debug
description: Diagnose and fix invisible or missing TikZ graphics in LaTeX PDFs. Use when user reports that tikzpicture compiles successfully but appears blank, invisible, or missing in the PDF output. Common symptoms include "tikzpicture not showing", "LaTeX figure is blank", "compiled but can't see the diagram".
---

# LaTeX TikZ Debugging

Systematic approach to diagnose and fix invisible or missing TikZ graphics in compiled PDFs.

## Diagnostic Workflow

When a user reports invisible TikZ graphics, follow this sequence:

### 1. Verify Compilation Success
- Check if PDF was actually generated
- Look for LaTeX errors in compilation log
- Confirm the figure reference number appears in text

### 2. Identify Root Cause

Run through these common issues in order:

**Issue A: Colors Too Light (Most Common)**
- Symptom: Figure area appears blank or nearly white
- Check for: `fill=color!10`, `fill=color!15` (< 20% saturation)
- Fix: Increase to 30-45% (e.g., `fill=blue!35`, `fill=green!40`)

**Issue B: Scalebox Rendering Failure**
- Symptom: Complete blank space where figure should be
- Check for: `\scalebox{...}{\begin{tikzpicture}...\end{tikzpicture}}`
- Fix: Remove scalebox, use `scale=0.8` or absolute coordinates instead

**Issue C: Relative Positioning Conflicts**
- Symptom: "Not allowed in LR mode" compilation errors
- Check for: `below=of node` combined with `\\` line breaks in node text
- Fix: Use absolute coordinates `at (x,y)` or `text width + align=center`

**Issue D: Fit Library Complexity**
- Symptom: Dashed boundary boxes missing or misplaced
- Check for: `fit=(node1)(node2)(node3)` in node options
- Fix: Manually draw with `\draw ... rectangle ...`

## Standard Fix Pattern

When multiple issues are present, apply this comprehensive fix:

```latex
% BEFORE (problematic)
\begin{figure}[htbp]
\centering
\scalebox{0.75}{
\begin{tikzpicture}[
    node distance=1.5cm,
    box/.style={fill=blue!10, draw=black}  % Too light!
]
\node[box, below=of input] (output) {Result\\Line 2};  % LR mode error!
\node[fit=(a)(b)] (boundary) {};  % Complex
\end{tikzpicture}
}
\end{figure}

% AFTER (fixed)
\begin{figure}[htbp]
\centering
\begin{tikzpicture}[
    box/.style={
        fill=blue!35,           % Visible color
        draw=black,
        line width=1pt,         % Clear border
        text width=3cm,         % Enable wrapping
        align=center            % Replace \\
    }
]
\node[box] (output) at (2,-3) {Result Line 2};  % Absolute position
\draw[dashed] (0,0) rectangle (5,-4);            % Manual boundary
\end{tikzpicture}
\end{figure}
```

## Key Fixes

### Fix 1: Enhance Colors
```latex
% Increase saturation from <20% to 30-45%
fill=blue!10   → fill=blue!35
fill=green!15  → fill=green!40
fill=yellow!20 → fill=yellow!45
fill=gray!10   → fill=gray!30
```

### Fix 2: Remove Scalebox
```latex
% Replace scalebox with internal scaling or absolute coordinates
\scalebox{0.8}{\begin{tikzpicture}...\end{tikzpicture}}
↓
\begin{tikzpicture}[scale=0.8, transform shape]...\end{tikzpicture}
% OR use absolute coordinates: \node at (x,y)
```

### Fix 3: Absolute Positioning
```latex
% Replace relative positioning with absolute coordinates
\node[style, below=2cm of other] (name) {Text\\Line2};
↓
\node[style, text width=3cm, align=center] (name) at (4,-3) {Text Line2};
```

### Fix 4: Manual Boundaries
```latex
% Replace fit with manual rectangle
\node[fit=(a)(b)(c), draw, dashed] (box) {};
↓
\draw[dashed, line width=1pt] (x1,y1) rectangle (x2,y2);
\node at (x,y) {Label};
```

## Quick Validation

After applying fixes, verify:
1. ✅ All colors ≥ 30% saturation
2. ✅ No `\scalebox` wrapping tikzpicture
3. ✅ Line widths ≥ 0.8pt (visible borders)
4. ✅ `text width + align=center` instead of `\\` for multiline text
5. ✅ Compilation completes without "Not allowed in LR mode" errors

## Prevention Tips

When creating new TikZ graphics:
- Start with 30-40% color saturation (not 10-15%)
- Use absolute coordinates `at (x,y)` from the beginning
- Add `line width=1pt` to all shape styles
- Avoid `\scalebox` - use `scale=` parameter or plan dimensions carefully
- Use `text width + align` for text wrapping, not `\\`

## Testing

After fixes, always:
1. Clean build: `rm main.pdf && xelatex main.tex`
2. **Close and reopen PDF viewer** (not just refresh)
3. Check the specific page number where figure should appear
4. Verify all colors and shapes are clearly visible

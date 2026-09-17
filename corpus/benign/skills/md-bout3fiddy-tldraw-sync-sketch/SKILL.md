---
name: sketch
description: Capture and analyze sketches from the tldraw canvas to understand user intent
triggers:
  - check the sketch
  - check my sketch
  - look at my sketch
  - analyze the sketch
  - what did I draw
---

# Sketch Analysis Skill

When the user asks you to check their sketch, follow these steps:

## Step 1: Capture the Screenshot

Take a screenshot of the current canvas using the API:

```bash
curl -s http://localhost:3001/api/screenshot -o /tmp/sketch-capture.png
```

## Step 2: Read and Analyze the Image

Use the Read tool to view the screenshot:

```
Read /tmp/sketch-capture.png
```

## Step 3: Analyze the Sketch

Look at the image and determine:
1. **What elements are drawn** - shapes, text, UI components, diagrams, etc.
2. **What the user likely wants** - based on the visual content
3. **Any annotations or notes** - text that provides context

## Step 4: Respond Based on Context

Depending on what you see, respond appropriately:

- **UI Mockup**: Describe the UI and offer to generate a component
- **Diagram/Flowchart**: Explain the flow and offer to document it
- **Annotation on overlay**: Provide feedback on the annotated UI
- **Freeform notes**: Summarize and offer next steps

## Design System Context

If generating components, use these design tokens:

**Colors:**
- Background: `#FAF7F2` (warm cream)
- Accent Gold: `#C8891A`
- Accent Blue-Green: `#0D98BA`
- Foreground: `#1a1a1a`

**Typography:**
- Labels/Buttons: Berkeley Mono (monospace), uppercase, tracking-wide
- Body: Rubik (sans-serif)
- Headlines: Playfair Display (serif)

**SolidJS Patterns:**
- Use `class=` not `className=`
- Use `<Show when={...}>` for conditionals
- Use `<For each={...}>` for lists

## Example Responses

### For a UI Sketch
"I see a card component with a header, image, and two buttons. Would you like me to generate a SolidJS component for this?"

### For Annotations
"I see you've circled an area and written 'too much spacing'. I can help adjust the padding in this component."

### For a Diagram
"This looks like a user flow diagram showing login → dashboard → settings. Would you like me to document this flow?"

## Prerequisites

- tldraw-sync must be running: `bun start`
- Both canvas (port 5173) and API server (port 3001) must be active

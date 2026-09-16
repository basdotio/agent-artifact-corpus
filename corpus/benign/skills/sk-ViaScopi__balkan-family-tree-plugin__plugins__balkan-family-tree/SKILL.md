---
name: balkan-family-tree
description: Comprehensive skill for working with Balkan Family Tree JS libraries (V1 and V2). Use when creating family tree visualizations, genealogy applications, org charts with family relationships, or when migrating between library versions. Covers initialization, data structures, templates, events, node manipulation, and V1→V2 migration patterns.
license: MIT - See LICENSE file
---

# Balkan Family Tree JS

Interactive family tree visualization library. Two major versions exist with different APIs.

## Version Selection

| Choose V2 when... | Choose V1 when... |
|-------------------|-------------------|
| Starting new project | Maintaining existing V1 codebase |
| Need latest features | Need V1-specific integrations |
| Modern API preferred | Backward compatibility required |

## Quick Reference

### V2 (Recommended for new projects)

```html
<script src="https://balkan.app/js/familytree.js"></script>
<div id="tree"></div>
<script>
var family = new FamilyTree(document.getElementById("tree"), {
    nodeBinding: {
        field_0: "name",
        img_0: "img"
    },
    nodes: [
        { id: 1, pids: [2], name: "Amber McKenzie", gender: "female", img: "photo.jpg" },
        { id: 2, pids: [1], name: "Ava Field", gender: "male", img: "photo2.jpg" },
        { id: 3, mid: 1, fid: 2, name: "Peter Stevens", gender: "male" }
    ]
});
</script>
```

### V1 (Legacy)

```html
<script src="https://balkan.app/js/FamilyTree.js"></script>
<div id="tree"></div>
<script>
var family = new FamilyTree(document.getElementById("tree"), {
    template: "john",
    nodeBinding: {
        field_0: "name"
    }
});
family.load([
    { id: 1, pids: [2], name: "Amber" },
    { id: 2, pids: [1], name: "Ava" },
    { id: 3, mid: 1, fid: 2, name: "Peter" }
]);
</script>
```

## Core Data Structure (Both Versions)

```javascript
{
    id: Number|String,      // Unique identifier (required)
    pids: Array,            // Partner IDs
    mid: Number|String,     // Mother ID
    fid: Number|String,     // Father ID
    name: String,           // Display name
    gender: "male"|"female",
    img: String,            // Photo URL
    // Custom fields allowed
}
```

## Detailed Documentation

- **V2 Full Guide**: See [references/v2-guide.md](references/v2-guide.md) for complete V2 API, templates, events, and advanced features
- **V1 Full Guide**: See [references/v1-guide.md](references/v1-guide.md) for complete V1 API and patterns
- **Migration Guide**: See [references/migration-v1-to-v2.md](references/migration-v1-to-v2.md) for converting V1 code to V2

## Common Tasks

### Adding Nodes Programmatically

**V2:**
```javascript
family.addNode({ id: 4, mid: 1, fid: 2, name: "New Child", gender: "female" });
```

**V1:**
```javascript
family.add({ id: 4, mid: 1, fid: 2, name: "New Child" });
```

### Handling Events

**V2:**
```javascript
family.onNodeClick((args) => {
    console.log("Clicked:", args.node);
});
```

**V1:**
```javascript
family.on("click", function(sender, args) {
    console.log("Clicked:", args.node);
});
```

### Exporting

**V2:**
```javascript
family.exportPDF();
family.exportPNG();
family.exportSVG();
```

**V1:**
```javascript
FamilyTree.pdfPrevUI.show(family, { format: "A4" });
FamilyTree.exportPNG(family, {});
```

## Workflow

1. **New Project**: Read [references/v2-guide.md](references/v2-guide.md) → implement with V2 API
2. **Existing V1 Project**: Read [references/v1-guide.md](references/v1-guide.md) → maintain with V1 API
3. **Migration**: Read [references/migration-v1-to-v2.md](references/migration-v1-to-v2.md) → convert systematically

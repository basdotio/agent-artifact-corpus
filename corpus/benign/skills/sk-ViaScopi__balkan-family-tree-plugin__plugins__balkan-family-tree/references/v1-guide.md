# Balkan Family Tree V1 Complete Guide

## Table of Contents
1. [Installation](#installation)
2. [Initialization](#initialization)
3. [Data Structure](#data-structure)
4. [Configuration Options](#configuration-options)
5. [Templates](#templates)
6. [Events](#events)
7. [Methods](#methods)
8. [Export](#export)

---

## Installation

### CDN
```html
<script src="https://balkan.app/js/FamilyTree.js"></script>
```

Note the capital 'F' and 'T' in V1 script name.

---

## Initialization

### Basic Setup
```javascript
var family = new FamilyTree(document.getElementById("tree"), {
    template: "john",
    nodeBinding: {
        field_0: "name"
    }
});

// Load data separately in V1
family.load([
    { id: 1, pids: [2], name: "John" },
    { id: 2, pids: [1], name: "Jane" },
    { id: 3, mid: 2, fid: 1, name: "Child" }
]);
```

### Key V1 Difference
V1 separates initialization from data loading:
```javascript
// 1. Create instance
var family = new FamilyTree(element, options);

// 2. Load data
family.load(nodes);
```

---

## Data Structure

Same structure as V2:

```javascript
{
    id: 1,              // Required: unique identifier
    pids: [2],          // Partner IDs
    mid: null,          // Mother ID
    fid: null,          // Father ID
    name: "John Smith",
    gender: "male",
    img: "photo.jpg"
}
```

### Complete Example
```javascript
var nodes = [
    { id: 1, pids: [2], name: "Grandfather", gender: "male" },
    { id: 2, pids: [1], name: "Grandmother", gender: "female" },
    { id: 3, mid: 2, fid: 1, pids: [4], name: "Father", gender: "male" },
    { id: 4, pids: [3], name: "Mother", gender: "female" },
    { id: 5, mid: 4, fid: 3, name: "Child 1", gender: "male" },
    { id: 6, mid: 4, fid: 3, name: "Child 2", gender: "female" }
];

family.load(nodes);
```

---

## Configuration Options

### Layout Options
```javascript
{
    orientation: FamilyTree.orientation.top,  // top, bottom, left, right
    levelSeparation: 100,
    siblingSeparation: 50,
    subtreeSeparation: 60
}
```

### Display Options
```javascript
{
    enableSearch: true,
    searchFields: ["name"],
    miniMap: true,
    scaleInitial: FamilyTree.match.boundary
}
```

### Complete Configuration
```javascript
var family = new FamilyTree(document.getElementById("tree"), {
    template: "tommy",
    orientation: FamilyTree.orientation.top,
    levelSeparation: 80,
    siblingSeparation: 40,
    enableSearch: true,
    miniMap: true,
    nodeBinding: {
        field_0: "name",
        field_1: "born",
        img_0: "img"
    }
});
```

---

## Templates

### Built-in Templates (V1)
- `john` - Default simple template
- `tommy` - Compact design
- `polly` - With circular images
- `olivia` - Elegant style

### Setting Template
```javascript
{
    template: "tommy"
}
```

### Custom Template (V1 Style)
```javascript
FamilyTree.templates.custom = Object.assign({}, FamilyTree.templates.john);

FamilyTree.templates.custom.size = [180, 80];

FamilyTree.templates.custom.node = 
    '<rect x="0" y="0" width="180" height="80" fill="#fff" stroke="#000" rx="5"></rect>';

FamilyTree.templates.custom.field_0 = 
    '<text x="90" y="25" text-anchor="middle">{val}</text>';

FamilyTree.templates.custom.field_1 = 
    '<text x="90" y="50" text-anchor="middle" fill="#666">{val}</text>';

FamilyTree.templates.custom.img_0 =
    '<image x="5" y="5" width="40" height="40" href="{val}"></image>';

// Apply to instance
var family = new FamilyTree(element, {
    template: "custom",
    ...
});
```

### Gender-Based Templates (V1)
```javascript
FamilyTree.templates.custom_male = Object.assign({}, FamilyTree.templates.custom);
FamilyTree.templates.custom_male.node = 
    '<rect x="0" y="0" width="180" height="80" fill="#e3f2fd" stroke="#1976D2" rx="5"></rect>';

FamilyTree.templates.custom_female = Object.assign({}, FamilyTree.templates.custom);
FamilyTree.templates.custom_female.node = 
    '<rect x="0" y="0" width="180" height="80" fill="#fce4ec" stroke="#c2185b" rx="5"></rect>';
```

---

## Events

### V1 Event Syntax
V1 uses `.on()` method with event name strings:

```javascript
family.on("click", function(sender, args) {
    console.log("Clicked node:", args.node);
});
```

### Available Events

#### Node Events
```javascript
// Click
family.on("click", function(sender, args) {
    console.log(args.node);
    return true;  // Return false to prevent default
});

// Double click
family.on("dbclick", function(sender, args) {
    console.log(args.node);
});

// Expand/Collapse
family.on("expcollclick", function(sender, args) {
    console.log("Node:", args.id, "Collapsed:", args.collapsed);
});
```

#### Data Events
```javascript
// After adding node
family.on("add", function(sender, args) {
    console.log("Added:", args.newData);
});

// After updating node
family.on("update", function(sender, args) {
    console.log("Updated:", args.newData);
});

// After removing node
family.on("remove", function(sender, args) {
    console.log("Removed:", args.id);
});
```

#### Tree Events
```javascript
// Redraw complete
family.on("redraw", function(sender) {
    console.log("Tree redrawn");
});

// Init complete
family.on("init", function(sender) {
    console.log("Tree initialized");
});
```

#### Edit Form Events
```javascript
family.editUI.on("show", function(sender, args) {
    console.log("Showing edit for:", args.id);
});

family.editUI.on("save", function(sender, args) {
    console.log("Saving:", args.data);
});

family.editUI.on("cancel", function(sender) {
    console.log("Edit cancelled");
});
```

---

## Methods

### Data Operations
```javascript
// Load data
family.load(nodes);

// Add node
family.add({ id: 10, name: "New Person" });

// Update node
family.update({ id: 10, name: "Updated Name" });

// Remove node
family.remove(10);

// Get node by ID
var node = family.get(10);
```

### Navigation
```javascript
// Center on node
family.center(nodeId);

// Expand node
family.expand(nodeId);

// Collapse node
family.collapse(nodeId);

// Fit to screen
family.fit();
```

### Tree Operations
```javascript
// Redraw
family.draw();

// Destroy
family.destroy();
```

### Search
```javascript
// Search
family.search("John");

// Clear search
family.clearSearch();
```

---

## Export

### PDF Export (V1)
```javascript
FamilyTree.pdfPrevUI.show(family, {
    format: "A4",
    orientation: "landscape"
});
```

### PNG Export (V1)
```javascript
FamilyTree.exportPNG(family, {
    filename: "family-tree.png"
});
```

### SVG Export (V1)
```javascript
FamilyTree.exportSVG(family, {
    filename: "family-tree.svg"
});
```

---

## V1-Specific Patterns

### Editing (V1)
```javascript
var family = new FamilyTree(document.getElementById("tree"), {
    enableEdit: true,
    nodeBinding: {
        field_0: "name"
    },
    editForm: {
        generateElementsFromStruct: true,
        elements: [
            { type: "textbox", label: "Name", binding: "name" },
            { type: "textbox", label: "Born", binding: "born" }
        ]
    }
});
```

### Initial Zoom/Position
```javascript
{
    scaleInitial: FamilyTree.match.boundary,
    scaleMin: 0.1,
    scaleMax: 2
}
```

### Drag and Drop
```javascript
{
    enableDragDrop: true
}

family.on("drop", function(sender, args) {
    console.log("Dropped:", args.dragNodeId, "onto:", args.dropNodeId);
    return true;
});
```

# Balkan Family Tree V2 Complete Guide

## Table of Contents
1. [Installation](#installation)
2. [Initialization](#initialization)
3. [Node Structure](#node-structure)
4. [Configuration Options](#configuration-options)
5. [Templates](#templates)
6. [Node Binding](#node-binding)
7. [Events](#events)
8. [Methods](#methods)
9. [Editing & Forms](#editing--forms)
10. [Export](#export)
11. [Advanced Features](#advanced-features)

---

## Installation

### CDN
```html
<script src="https://balkan.app/js/familytree.js"></script>
```

### NPM
```bash
npm install @nicealex/family-tree-js
```

```javascript
import FamilyTree from '@nicealex/family-tree-js';
```

---

## Initialization

### Basic Setup
```javascript
var family = new FamilyTree(document.getElementById("tree"), {
    nodeBinding: {
        field_0: "name",
        field_1: "born",
        img_0: "img"
    },
    nodes: [
        { id: 1, pids: [2], name: "John", gender: "male", born: "1965" },
        { id: 2, pids: [1], name: "Jane", gender: "female", born: "1967" },
        { id: 3, mid: 2, fid: 1, name: "Child", gender: "male", born: "1990" }
    ]
});
```

### With AJAX Data
```javascript
var family = new FamilyTree(document.getElementById("tree"), {
    nodeBinding: { field_0: "name" }
});

fetch('/api/family-data')
    .then(res => res.json())
    .then(data => family.load(data));
```

---

## Node Structure

### Required Properties
```javascript
{
    id: 1  // Unique identifier (Number or String)
}
```

### Relationship Properties
```javascript
{
    id: 3,
    mid: 1,        // Mother's ID
    fid: 2,        // Father's ID
    pids: [4, 5],  // Partner IDs (array for multiple marriages)
}
```

### Common Properties
```javascript
{
    id: 1,
    name: "John Smith",
    gender: "male",        // "male" | "female"
    img: "path/photo.jpg", // Photo URL
    born: "1965-03-15",
    died: "2020-01-10",
    // Any custom properties allowed
    occupation: "Engineer",
    location: "New York"
}
```

### Multiple Partners Example
```javascript
nodes: [
    { id: 1, pids: [2, 3], name: "Person with 2 spouses" },
    { id: 2, pids: [1], name: "First Spouse" },
    { id: 3, pids: [1], name: "Second Spouse" },
    { id: 4, mid: 2, fid: 1, name: "Child from first marriage" },
    { id: 5, mid: 3, fid: 1, name: "Child from second marriage" }
]
```

---

## Configuration Options

### Layout Options
```javascript
{
    orientation: FamilyTree.orientation.top, // top, bottom, left, right
    levelSeparation: 100,      // Vertical spacing between levels
    siblingSeparation: 50,     // Horizontal spacing between siblings
    subtreeSeparation: 60,     // Spacing between subtrees
    mixedHierarchyNodesSeparation: 10,
}
```

### Display Options
```javascript
{
    scaleInitial: FamilyTree.match.boundary,  // Initial zoom
    scaleMin: 0.1,
    scaleMax: 2,
    enableSearch: true,
    searchFields: ["name", "born", "location"],
    searchFieldsWeight: { name: 100, born: 50 },
    miniMap: true,
    sticky: true,  // Keep partners together
}
```

### Interaction Options
```javascript
{
    enableDragDrop: true,
    mouseScrool: FamilyTree.action.zoom,  // zoom | ctrlZoom | none
    showXScroll: FamilyTree.scroll.visible,
    showYScroll: FamilyTree.scroll.visible,
}
```

### Complete Example
```javascript
var family = new FamilyTree(document.getElementById("tree"), {
    template: "hugo",
    orientation: FamilyTree.orientation.top,
    levelSeparation: 100,
    siblingSeparation: 50,
    enableSearch: true,
    searchFields: ["name", "born"],
    miniMap: true,
    nodeBinding: {
        field_0: "name",
        field_1: "born",
        img_0: "img"
    },
    nodes: [...]
});
```

---

## Templates

### Built-in Templates
- `hugo` - Modern card style (default)
- `tommy` - Compact style
- `polly` - Circular photos
- `olivia` - Elegant style
- `deborah` - Classic style
- `john` - Simple style

### Setting Template
```javascript
{
    template: "hugo"
}
```

### Custom Template
```javascript
FamilyTree.templates.myTemplate = Object.assign({}, FamilyTree.templates.hugo);
FamilyTree.templates.myTemplate.size = [200, 100];
FamilyTree.templates.myTemplate.node = 
    '<rect x="0" y="0" width="200" height="100" fill="#ffffff" stroke="#ccc" rx="10"></rect>';

// Field positioning
FamilyTree.templates.myTemplate.field_0 = 
    '<text x="100" y="30" text-anchor="middle">{val}</text>';
FamilyTree.templates.myTemplate.field_1 = 
    '<text x="100" y="55" text-anchor="middle" fill="#888">{val}</text>';

// Image
FamilyTree.templates.myTemplate.img_0 = 
    '<clipPath id="{randId}"><circle cx="40" cy="50" r="30"></circle></clipPath>' +
    '<image x="10" y="20" width="60" height="60" clip-path="url(#{randId})" href="{val}"></image>';

// Gender-specific colors
FamilyTree.templates.myTemplate_male = Object.assign({}, FamilyTree.templates.myTemplate);
FamilyTree.templates.myTemplate_male.node = 
    '<rect x="0" y="0" width="200" height="100" fill="#e3f2fd" stroke="#1976D2" rx="10"></rect>';

FamilyTree.templates.myTemplate_female = Object.assign({}, FamilyTree.templates.myTemplate);
FamilyTree.templates.myTemplate_female.node = 
    '<rect x="0" y="0" width="200" height="100" fill="#fce4ec" stroke="#c2185b" rx="10"></rect>';

// Use template
var family = new FamilyTree(document.getElementById("tree"), {
    template: "myTemplate",
    ...
});
```

### Per-Node Template
```javascript
nodes: [
    { id: 1, name: "John", tags: ["vip"] }
]

// Define tag template
FamilyTree.templates.vip = Object.assign({}, FamilyTree.templates.hugo);
FamilyTree.templates.vip.node = '<rect ... fill="gold" ...></rect>';
```

---

## Node Binding

Maps data properties to template fields.

```javascript
nodeBinding: {
    field_0: "name",        // First text field
    field_1: "title",       // Second text field
    field_2: "department",  // Third text field
    img_0: "photo",         // Image field
    img_1: "flag"           // Second image (if template supports)
}
```

### Dynamic Binding
```javascript
nodeBinding: {
    field_0: function(sender, node) {
        return node.name + " (" + node.born + ")";
    },
    field_1: function(sender, node) {
        if (node.died) return "☆ " + node.born + " † " + node.died;
        return "Born: " + node.born;
    }
}
```

---

## Events

### Node Events
```javascript
// Click
family.onNodeClick((args) => {
    console.log("Node clicked:", args.node);
    return true; // Return false to prevent default
});

// Double click
family.onNodeDoubleClick((args) => {
    console.log("Node double-clicked:", args.node);
});

// Expand/Collapse
family.onExpandCollapse((args) => {
    console.log("Node expanded/collapsed:", args.id, args.expand);
});
```

### Data Events
```javascript
// Node added
family.onNodeAdded((args) => {
    console.log("Node added:", args.node);
});

// Node updated
family.onNodeUpdated((args) => {
    console.log("Node updated:", args.node);
});

// Node removed
family.onNodeRemoved((args) => {
    console.log("Node removed:", args.id);
});
```

### Tree Events
```javascript
// After redraw
family.onRedraw(() => {
    console.log("Tree redrawn");
});

// Init complete
family.onInit(() => {
    console.log("Tree initialized");
});
```

### Edit Form Events
```javascript
family.editUI.on('show', function(sender, args) {
    console.log("Edit form shown for:", args.id);
});

family.editUI.on('save', function(sender, args) {
    console.log("Saving:", args.data);
});

family.editUI.on('cancel', function(sender, args) {
    console.log("Edit cancelled");
});
```

---

## Methods

### Node Operations
```javascript
// Add node
family.addNode({ id: 10, name: "New Person" });

// Update node
family.updateNode({ id: 10, name: "Updated Name" });

// Remove node
family.removeNode(10);

// Get node
var node = family.getNode(10);

// Get all nodes
var nodes = family.nodes;
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
// Load data
family.load([...nodes]);

// Clear
family.load([]);

// Redraw
family.draw();

// Destroy instance
family.destroy();
```

### Search
```javascript
// Programmatic search
family.search("John");

// Clear search
family.clearSearch();
```

---

## Editing & Forms

### Enable Built-in Editing
```javascript
var family = new FamilyTree(document.getElementById("tree"), {
    editForm: {
        generateElementsFromStruct: true,
        elements: [
            { type: "textbox", label: "Name", binding: "name" },
            { type: "textbox", label: "Born", binding: "born" },
            { type: "select", label: "Gender", binding: "gender", 
              options: [{value: "male", text: "Male"}, {value: "female", text: "Female"}] }
        ],
        buttons: {
            edit: { icon: FamilyTree.icon.edit(24, 24, "#fff"), text: "Edit" },
            share: null,  // Hide share button
            pdf: null     // Hide PDF button
        }
    },
    ...
});
```

### Edit Form Element Types
- `textbox` - Text input
- `select` - Dropdown
- `date` - Date picker
- `checkbox` - Boolean
- `textarea` - Multi-line text

### Custom Edit Form
```javascript
family.editUI.on('show', function(sender, args) {
    var node = family.getNode(args.id);
    // Build custom form HTML
    sender.content = `
        <div class="custom-form">
            <input id="name-input" value="${node.name}">
            <button onclick="saveNode(${args.id})">Save</button>
        </div>
    `;
});

function saveNode(id) {
    var name = document.getElementById("name-input").value;
    family.updateNode({ id: id, name: name });
    family.editUI.hide();
}
```

---

## Export

### PDF Export
```javascript
// Simple
family.exportPDF();

// With options
family.exportPDF({
    format: "A4",
    orientation: "landscape",
    margin: [10, 10, 10, 10],
    header: "My Family Tree",
    footer: "Page {page}"
});
```

### PNG Export
```javascript
family.exportPNG({
    filename: "family-tree.png"
});
```

### SVG Export
```javascript
family.exportSVG({
    filename: "family-tree.svg"
});
```

### Export to JSON
```javascript
var jsonData = JSON.stringify(family.nodes);
```

---

## Advanced Features

### Lazy Loading (Large Trees)
```javascript
var family = new FamilyTree(document.getElementById("tree"), {
    lazyLoading: true,
    ...
});

family.onLazyLoad((args) => {
    // Fetch children for expanded node
    fetch(`/api/children/${args.id}`)
        .then(res => res.json())
        .then(children => {
            args.loaded(children);
        });
});
```

### Tags for Conditional Styling
```javascript
nodes: [
    { id: 1, name: "VIP Person", tags: ["vip", "founder"] },
    { id: 2, name: "Regular", tags: [] }
]

// Define tag templates
FamilyTree.templates.vip = Object.assign({}, FamilyTree.templates.hugo);
FamilyTree.templates.vip.node = '<rect ... fill="#ffd700" ...>';
```

### Collapse/Expand Control
```javascript
// Expand all
family.expandAll();

// Collapse all  
family.collapseAll();

// Set initial collapsed state
nodes: [
    { id: 1, name: "Root", collapsed: true }  // Children hidden initially
]
```

### Animation
```javascript
{
    anim: {
        func: FamilyTree.anim.outPow,
        duration: 500
    }
}
```

### Filtering
```javascript
family.filter(function(node) {
    return node.gender === "male";
});

// Clear filter
family.clearFilter();
```

### Undo/Redo
```javascript
family.undoStepsCount = 10;  // Enable undo with 10 steps

// Undo
family.undo();

// Redo
family.redo();
```

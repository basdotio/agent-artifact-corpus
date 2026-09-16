# V1 to V2 Migration Guide

## Table of Contents
1. [Overview](#overview)
2. [Script/Package Changes](#scriptpackage-changes)
3. [Initialization Changes](#initialization-changes)
4. [Event System Changes](#event-system-changes)
5. [Method Changes](#method-changes)
6. [Export Changes](#export-changes)
7. [Complete Migration Checklist](#complete-migration-checklist)
8. [Migration Script](#migration-script)

---

## Overview

Major differences between V1 and V2:
- Data loading is now part of initialization options
- Event binding uses new callback-style syntax
- Some method names changed
- Export APIs simplified

---

## Script/Package Changes

### CDN URL
```html
<!-- V1 -->
<script src="https://balkan.app/js/FamilyTree.js"></script>

<!-- V2 -->
<script src="https://balkan.app/js/familytree.js"></script>
```

Note: Different casing in URL (FamilyTree.js → familytree.js)

### NPM Package
```javascript
// V1
import FamilyTree from 'family-tree-js';

// V2
import FamilyTree from '@nicealex/family-tree-js';
```

---

## Initialization Changes

### Data Loading

**V1 - Separate load call:**
```javascript
var family = new FamilyTree(document.getElementById("tree"), {
    template: "john",
    nodeBinding: { field_0: "name" }
});
family.load(nodes);  // Separate call
```

**V2 - Nodes in options:**
```javascript
var family = new FamilyTree(document.getElementById("tree"), {
    template: "hugo",
    nodeBinding: { field_0: "name" },
    nodes: nodes  // Part of initialization
});
```

### Conversion Pattern
```javascript
// V1
var family = new FamilyTree(el, options);
family.load(data);

// V2
var family = new FamilyTree(el, {
    ...options,
    nodes: data
});
```

---

## Event System Changes

### Event Binding Syntax

**V1 - String-based `.on()` method:**
```javascript
family.on("click", function(sender, args) {
    console.log(args.node);
});
```

**V2 - Callback methods:**
```javascript
family.onNodeClick((args) => {
    console.log(args.node);
});
```

### Event Name Mapping

| V1 Event | V2 Method |
|----------|-----------|
| `family.on("click", fn)` | `family.onNodeClick(fn)` |
| `family.on("dbclick", fn)` | `family.onNodeDoubleClick(fn)` |
| `family.on("add", fn)` | `family.onNodeAdded(fn)` |
| `family.on("update", fn)` | `family.onNodeUpdated(fn)` |
| `family.on("remove", fn)` | `family.onNodeRemoved(fn)` |
| `family.on("redraw", fn)` | `family.onRedraw(fn)` |
| `family.on("init", fn)` | `family.onInit(fn)` |
| `family.on("expcollclick", fn)` | `family.onExpandCollapse(fn)` |
| `family.on("drop", fn)` | `family.onDrop(fn)` |

### Callback Arguments

**V1 - Two arguments (sender, args):**
```javascript
family.on("click", function(sender, args) {
    // sender = FamilyTree instance
    // args = event data
});
```

**V2 - Single argument (args):**
```javascript
family.onNodeClick((args) => {
    // args = event data
    // Access tree via: family (closure) or args.sender
});
```

### Complete Event Conversion Examples

```javascript
// V1
family.on("click", function(sender, args) {
    sender.center(args.node.id);
    return false;  // Prevent default
});

// V2
family.onNodeClick((args) => {
    family.center(args.node.id);
    return false;  // Prevent default
});

// V1
family.on("add", function(sender, args) {
    saveToServer(args.newData);
});

// V2
family.onNodeAdded((args) => {
    saveToServer(args.node);
});

// V1
family.on("update", function(sender, args) {
    updateOnServer(args.newData);
});

// V2
family.onNodeUpdated((args) => {
    updateOnServer(args.node);
});
```

---

## Method Changes

### Node Operations

| V1 Method | V2 Method |
|-----------|-----------|
| `family.add(node)` | `family.addNode(node)` |
| `family.update(node)` | `family.updateNode(node)` |
| `family.remove(id)` | `family.removeNode(id)` |
| `family.get(id)` | `family.getNode(id)` |

### Example Conversions

```javascript
// V1
family.add({ id: 10, name: "New" });
family.update({ id: 10, name: "Updated" });
family.remove(10);
var node = family.get(5);

// V2
family.addNode({ id: 10, name: "New" });
family.updateNode({ id: 10, name: "Updated" });
family.removeNode(10);
var node = family.getNode(5);
```

### Unchanged Methods
These methods remain the same:
- `family.load(nodes)`
- `family.center(id)`
- `family.expand(id)`
- `family.collapse(id)`
- `family.fit()`
- `family.draw()`
- `family.destroy()`
- `family.search(query)`
- `family.clearSearch()`

---

## Export Changes

### PDF Export

**V1:**
```javascript
FamilyTree.pdfPrevUI.show(family, {
    format: "A4",
    orientation: "landscape"
});
```

**V2:**
```javascript
family.exportPDF({
    format: "A4",
    orientation: "landscape"
});
```

### PNG Export

**V1:**
```javascript
FamilyTree.exportPNG(family, {
    filename: "tree.png"
});
```

**V2:**
```javascript
family.exportPNG({
    filename: "tree.png"
});
```

### SVG Export

**V1:**
```javascript
FamilyTree.exportSVG(family, {
    filename: "tree.svg"
});
```

**V2:**
```javascript
family.exportSVG({
    filename: "tree.svg"
});
```

---

## Complete Migration Checklist

### 1. Update Script Reference
- [ ] Change CDN URL from `FamilyTree.js` to `familytree.js`
- [ ] Or update npm package to `@nicealex/family-tree-js`

### 2. Update Initialization
- [ ] Move `family.load(nodes)` data into options as `nodes: data`

### 3. Update Events
- [ ] Convert `.on("click", fn)` to `.onNodeClick(fn)`
- [ ] Convert `.on("dbclick", fn)` to `.onNodeDoubleClick(fn)`
- [ ] Convert `.on("add", fn)` to `.onNodeAdded(fn)`
- [ ] Convert `.on("update", fn)` to `.onNodeUpdated(fn)`
- [ ] Convert `.on("remove", fn)` to `.onNodeRemoved(fn)`
- [ ] Convert `.on("redraw", fn)` to `.onRedraw(fn)`
- [ ] Convert `.on("init", fn)` to `.onInit(fn)`
- [ ] Update callback signatures (remove `sender` first argument)

### 4. Update Methods
- [ ] Replace `family.add()` with `family.addNode()`
- [ ] Replace `family.update()` with `family.updateNode()`
- [ ] Replace `family.remove()` with `family.removeNode()`
- [ ] Replace `family.get()` with `family.getNode()`

### 5. Update Exports
- [ ] Replace `FamilyTree.pdfPrevUI.show(family, opts)` with `family.exportPDF(opts)`
- [ ] Replace `FamilyTree.exportPNG(family, opts)` with `family.exportPNG(opts)`
- [ ] Replace `FamilyTree.exportSVG(family, opts)` with `family.exportSVG(opts)`

### 6. Test
- [ ] Verify tree renders correctly
- [ ] Test all event handlers
- [ ] Test all CRUD operations
- [ ] Test export functionality

---

## Migration Script

Use this Node.js script to assist with migrating V1 code to V2:

```javascript
/**
 * Balkan Family Tree V1 to V2 Migration Helper
 * Run: node migrate-family-tree.js input.js output.js
 */

const fs = require('fs');

function migrateCode(code) {
    let result = code;
    
    // Script URL
    result = result.replace(
        /balkan\.app\/js\/FamilyTree\.js/g,
        'balkan.app/js/familytree.js'
    );
    
    // Event conversions
    const eventMap = {
        '"click"': 'onNodeClick',
        "'click'": 'onNodeClick',
        '"dbclick"': 'onNodeDoubleClick',
        "'dbclick'": 'onNodeDoubleClick',
        '"add"': 'onNodeAdded',
        "'add'": 'onNodeAdded',
        '"update"': 'onNodeUpdated',
        "'update'": 'onNodeUpdated',
        '"remove"': 'onNodeRemoved',
        "'remove'": 'onNodeRemoved',
        '"redraw"': 'onRedraw',
        "'redraw'": 'onRedraw',
        '"init"': 'onInit',
        "'init'": 'onInit',
        '"expcollclick"': 'onExpandCollapse',
        "'expcollclick'": 'onExpandCollapse',
        '"drop"': 'onDrop',
        "'drop'": 'onDrop'
    };
    
    for (const [v1Event, v2Method] of Object.entries(eventMap)) {
        // Pattern: .on("event", function(sender, args) { ... })
        const regex = new RegExp(
            `\\.on\\(${v1Event.replace(/['"]/g, '[\'"]')},\\s*function\\s*\\(\\s*sender\\s*,\\s*args\\s*\\)`,
            'g'
        );
        result = result.replace(regex, `.${v2Method}((args)`);
    }
    
    // Method conversions
    result = result.replace(/\.add\s*\(\s*\{/g, '.addNode({');
    result = result.replace(/\.update\s*\(\s*\{/g, '.updateNode({');
    result = result.replace(/\.remove\s*\(/g, '.removeNode(');
    result = result.replace(/\.get\s*\(\s*(\d+)\s*\)/g, '.getNode($1)');
    
    // Export conversions
    result = result.replace(
        /FamilyTree\.pdfPrevUI\.show\s*\(\s*(\w+)\s*,/g,
        '$1.exportPDF('
    );
    result = result.replace(
        /FamilyTree\.exportPNG\s*\(\s*(\w+)\s*,/g,
        '$1.exportPNG('
    );
    result = result.replace(
        /FamilyTree\.exportSVG\s*\(\s*(\w+)\s*,/g,
        '$1.exportSVG('
    );
    
    // Add migration comments for manual review
    if (result.includes('.load(')) {
        result = '// TODO: Move .load() data into initialization options as "nodes: data"\n' + result;
    }
    
    return result;
}

// CLI usage
if (process.argv.length >= 4) {
    const input = fs.readFileSync(process.argv[2], 'utf8');
    const output = migrateCode(input);
    fs.writeFileSync(process.argv[3], output);
    console.log(`Migrated ${process.argv[2]} -> ${process.argv[3]}`);
    console.log('Review the output for any remaining manual changes needed.');
} else {
    console.log('Usage: node migrate-family-tree.js input.js output.js');
}
```

---

## Side-by-Side Example

### Complete V1 Application

```javascript
// V1 Code
<script src="https://balkan.app/js/FamilyTree.js"></script>

var family = new FamilyTree(document.getElementById("tree"), {
    template: "john",
    nodeBinding: {
        field_0: "name",
        field_1: "born"
    }
});

family.load([
    { id: 1, pids: [2], name: "John", born: "1960" },
    { id: 2, pids: [1], name: "Jane", born: "1962" },
    { id: 3, mid: 2, fid: 1, name: "Child", born: "1985" }
]);

family.on("click", function(sender, args) {
    console.log("Clicked:", args.node.name);
    return true;
});

family.on("update", function(sender, args) {
    saveToServer(args.newData);
});

document.getElementById("add-btn").onclick = function() {
    family.add({ id: 4, name: "New Person" });
};

document.getElementById("export-btn").onclick = function() {
    FamilyTree.pdfPrevUI.show(family, { format: "A4" });
};
```

### Equivalent V2 Application

```javascript
// V2 Code
<script src="https://balkan.app/js/familytree.js"></script>

var family = new FamilyTree(document.getElementById("tree"), {
    template: "hugo",
    nodeBinding: {
        field_0: "name",
        field_1: "born"
    },
    nodes: [
        { id: 1, pids: [2], name: "John", born: "1960" },
        { id: 2, pids: [1], name: "Jane", born: "1962" },
        { id: 3, mid: 2, fid: 1, name: "Child", born: "1985" }
    ]
});

family.onNodeClick((args) => {
    console.log("Clicked:", args.node.name);
    return true;
});

family.onNodeUpdated((args) => {
    saveToServer(args.node);
});

document.getElementById("add-btn").onclick = function() {
    family.addNode({ id: 4, name: "New Person" });
};

document.getElementById("export-btn").onclick = function() {
    family.exportPDF({ format: "A4" });
};
```

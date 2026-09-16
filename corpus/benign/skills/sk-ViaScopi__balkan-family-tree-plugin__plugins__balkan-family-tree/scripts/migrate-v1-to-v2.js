#!/usr/bin/env node
/**
 * Balkan Family Tree V1 to V2 Migration Helper
 * 
 * Usage: node migrate-v1-to-v2.js <input-file> [output-file]
 * 
 * If output-file is not specified, prints to stdout.
 * 
 * This script performs automated conversions for:
 * - Script URL references
 * - Event handler syntax
 * - Method name changes
 * - Export API changes
 * 
 * Manual review is required for:
 * - Moving .load() data into initialization options
 * - Updating event callback signatures
 */

const fs = require('fs');
const path = require('path');

const MIGRATIONS = [
    // Script URL change
    {
        name: 'Script URL',
        pattern: /balkan\.app\/js\/FamilyTree\.js/g,
        replacement: 'balkan.app/js/familytree.js'
    },
    
    // Event handler conversions (with function(sender, args) signature)
    {
        name: 'click event',
        pattern: /\.on\(\s*["']click["']\s*,\s*function\s*\(\s*sender\s*,\s*args\s*\)/g,
        replacement: '.onNodeClick((args) =>'
    },
    {
        name: 'dbclick event',
        pattern: /\.on\(\s*["']dbclick["']\s*,\s*function\s*\(\s*sender\s*,\s*args\s*\)/g,
        replacement: '.onNodeDoubleClick((args) =>'
    },
    {
        name: 'add event',
        pattern: /\.on\(\s*["']add["']\s*,\s*function\s*\(\s*sender\s*,\s*args\s*\)/g,
        replacement: '.onNodeAdded((args) =>'
    },
    {
        name: 'update event',
        pattern: /\.on\(\s*["']update["']\s*,\s*function\s*\(\s*sender\s*,\s*args\s*\)/g,
        replacement: '.onNodeUpdated((args) =>'
    },
    {
        name: 'remove event',
        pattern: /\.on\(\s*["']remove["']\s*,\s*function\s*\(\s*sender\s*,\s*args\s*\)/g,
        replacement: '.onNodeRemoved((args) =>'
    },
    {
        name: 'redraw event',
        pattern: /\.on\(\s*["']redraw["']\s*,\s*function\s*\(\s*sender\s*\)/g,
        replacement: '.onRedraw(() =>'
    },
    {
        name: 'init event',
        pattern: /\.on\(\s*["']init["']\s*,\s*function\s*\(\s*sender\s*\)/g,
        replacement: '.onInit(() =>'
    },
    {
        name: 'expcollclick event',
        pattern: /\.on\(\s*["']expcollclick["']\s*,\s*function\s*\(\s*sender\s*,\s*args\s*\)/g,
        replacement: '.onExpandCollapse((args) =>'
    },
    {
        name: 'drop event',
        pattern: /\.on\(\s*["']drop["']\s*,\s*function\s*\(\s*sender\s*,\s*args\s*\)/g,
        replacement: '.onDrop((args) =>'
    },
    
    // Method name conversions
    {
        name: 'add() method',
        pattern: /\.add\s*\(\s*\{/g,
        replacement: '.addNode({'
    },
    {
        name: 'update() method',
        pattern: /\.update\s*\(\s*\{/g,
        replacement: '.updateNode({'
    },
    {
        name: 'remove() method',
        pattern: /\.remove\s*\(\s*([^)]+)\s*\)/g,
        replacement: '.removeNode($1)'
    },
    {
        name: 'get() method',
        pattern: /\.get\s*\(\s*([^)]+)\s*\)/g,
        replacement: '.getNode($1)'
    },
    
    // Export API conversions
    {
        name: 'PDF export',
        pattern: /FamilyTree\.pdfPrevUI\.show\s*\(\s*(\w+)\s*,\s*/g,
        replacement: '$1.exportPDF('
    },
    {
        name: 'PNG export',
        pattern: /FamilyTree\.exportPNG\s*\(\s*(\w+)\s*,\s*/g,
        replacement: '$1.exportPNG('
    },
    {
        name: 'SVG export',
        pattern: /FamilyTree\.exportSVG\s*\(\s*(\w+)\s*,\s*/g,
        replacement: '$1.exportSVG('
    }
];

function migrateCode(code) {
    let result = code;
    const changes = [];
    
    for (const migration of MIGRATIONS) {
        const matches = result.match(migration.pattern);
        if (matches && matches.length > 0) {
            result = result.replace(migration.pattern, migration.replacement);
            changes.push({
                name: migration.name,
                count: matches.length
            });
        }
    }
    
    // Check for patterns that need manual review
    const warnings = [];
    
    if (result.includes('.load(')) {
        warnings.push('Found .load() call - move data into initialization options as "nodes: data"');
    }
    
    if (result.includes('args.newData')) {
        warnings.push('Found args.newData - in V2, use args.node instead');
    }
    
    if (result.includes('sender.')) {
        warnings.push('Found sender. references - V2 callbacks receive only args, use closure or args.sender');
    }
    
    return { result, changes, warnings };
}

function main() {
    const args = process.argv.slice(2);
    
    if (args.length === 0) {
        console.log('Balkan Family Tree V1 to V2 Migration Helper');
        console.log('');
        console.log('Usage: node migrate-v1-to-v2.js <input-file> [output-file]');
        console.log('');
        console.log('If output-file is not specified, prints to stdout.');
        process.exit(1);
    }
    
    const inputFile = args[0];
    const outputFile = args[1];
    
    if (!fs.existsSync(inputFile)) {
        console.error(`Error: Input file not found: ${inputFile}`);
        process.exit(1);
    }
    
    const inputCode = fs.readFileSync(inputFile, 'utf8');
    const { result, changes, warnings } = migrateCode(inputCode);
    
    // Output results
    if (outputFile) {
        fs.writeFileSync(outputFile, result);
        console.log(`Migrated: ${inputFile} -> ${outputFile}`);
    } else {
        console.log(result);
    }
    
    // Print summary to stderr so it doesn't interfere with stdout output
    if (changes.length > 0 || warnings.length > 0) {
        console.error('');
        console.error('=== Migration Summary ===');
        
        if (changes.length > 0) {
            console.error('');
            console.error('Automated changes:');
            for (const change of changes) {
                console.error(`  ✓ ${change.name}: ${change.count} occurrence(s)`);
            }
        }
        
        if (warnings.length > 0) {
            console.error('');
            console.error('Manual review required:');
            for (const warning of warnings) {
                console.error(`  ⚠ ${warning}`);
            }
        }
        
        console.error('');
    }
}

main();

---
name: upgrading-packages
description: Safely upgrade frameworks and packages one at a time by analyzing breaking changes, new features, and required code adjustments. Use when Dependabot or Renovate suggests package updates, when the user asks to upgrade a specific package, or when upgrading Hugo, Tailwind CSS, DaisyUI, or other frontend frameworks.
---

# Package & Framework Upgrade Assistant

## Overview

This skill helps safely upgrade packages and frameworks by analyzing:
- Breaking changes requiring code modifications
- New features that could improve the application
- Compatibility issues with existing code
- Required configuration changes

**ALWAYS upgrade ONE package at a time** to isolate issues.

## Upgrade workflow

Copy this checklist and track progress:

```
Upgrade Progress:
- [ ] Step 1: Analyze current usage in codebase
- [ ] Step 2: Review release notes and breaking changes
- [ ] Step 3: Identify code adjustments needed
- [ ] Step 4: Check for beneficial new features
- [ ] Step 5: Create upgrade plan
- [ ] Step 6: Apply changes
- [ ] Step 7: Verify functionality
```

### Step 1: Analyze current usage

**For npm packages**: Search the codebase to understand how the package is currently used:

```bash
# Find all imports and usage in JavaScript files
grep -r "<package_name>" --include="*.js" layouts/ static/
# Check package.json dependencies
cat package.json
```

**For Python scripts**: Search for usage in Python files:

```bash
# Find all imports and usage in Python scripts
grep -r "import <package_name>" --include="*.py" scripts/
grep -r "from <package_name>" --include="*.py" scripts/
```

**For Hugo**: Check current version and usage:

```bash
# Check Hugo version
hugo version
# Check Hugo configuration
cat hugo.toml
```

**For Tailwind CSS/DaisyUI**: Check usage in templates and styles:

```bash
# Check version in package.json
grep -E "tailwindcss|daisyui" package.json
# Check usage in layouts
grep -r "class=" layouts/ --include="*.html" | head -20
# Check custom CSS
cat assets/css/main.css
```

Document:
- Which files use this package/framework
- What features/functions are being used
- How critical the package is to core functionality
- Current configuration files (tailwind.config.js, hugo.toml, etc.)

### Step 2: Review release notes

**If user provides release notes**: Use them as primary source

**If release notes missing or incomplete**: Fetch documentation using Context7 MCP server:

1. Resolve the library ID:
   ```
   Use mcp_io_github_ups_resolve-library-id with libraryName="<package_name>"
   ```

2. Get relevant documentation:
   ```
   Use mcp_io_github_ups_get-library-docs with:
   - context7CompatibleLibraryID from step 1
   - topic="breaking changes migration guide"
   - mode="info" (for migration guides)
   ```

3. If needed, get API changes:
   ```
   Use mcp_io_github_ups_get-library-docs with:
   - Same library ID
   - topic="api changes new features"
   - mode="code" (for code examples)
   ```

Focus on:
- Breaking changes between current and target version
- Deprecated features in use
- Migration guides
- New recommended patterns

### Step 3: Identify required code adjustments

Cross-reference Step 1 usage with Step 2 breaking changes:

For each breaking change:
1. Check if it affects code found in Step 1
2. Identify specific files and line numbers needing updates
3. Determine the required modification

Create a structured list:
```
File: path/to/file.py
Line: 45
Current: old_function(param)
Required: new_function(param, new_required_arg)
Reason: Function signature changed in v2.0
```

### Step 4: Check for beneficial new features

Review new features from release notes and identify improvements:

**Consider new features that**:
- Improve performance for existing functionality
- Simplify current implementation patterns
- Add error handling or logging capabilities
- Provide better type hints or async support

**Context for this application**:
- **Hugo static site generator**: Content management, template rendering
- **Tailwind CSS v4 + DaisyUI**: Styling framework and component library
- **Fuse.js**: Client-side fuzzy search for recipes
- **Recipe content**: Markdown files with YAML frontmatter in content/
- **Python scripts**: Recipe management tools (normalize, validate, search)
- **GitHub Pages**: Static site deployment under /CookBook/ path
- **Decap CMS**: Admin interface for content editing
- **Asset pipeline**: Image optimization, CSS/JS processing

Example analysis format:
```
New Feature: Hugo Pipes improvements in v0.120.0
Benefit: Better asset processing and caching for Tailwind CSS
Location: Could optimize assets/css/main.css processing
Effort: Low - mostly configuration changes
Priority: Medium - performance improvement for build times
```

### Step 5: Create upgrade plan

Synthesize findings into actionable plan:

```markdown
## Upgrade Plan: <package_name> from v<current> to v<target>

### Critical Changes (MUST DO)
1. [File path] - [Specific change needed]
2. [File path] - [Specific change needed]

### Configuration Updates
- **For npm packages**: Update package.json: <package_name>@<new_version>
- **For Hugo**: Update binaries via package manager or download
- **For Python scripts**: No requirements.txt, packages used ad-hoc
- [Any other config changes like tailwind.config.js, hugo.toml]

### Recommended Improvements (OPTIONAL)
1. [New feature] - [Where to apply] - [Expected benefit]

### Testing Strategy
- [ ] Run npm build: `npm run build`
- [ ] Test search functionality: `npm run test:search:v7`
- [ ] Run Hugo dev server: `npm run dev` or `hugo server -D`
- [ ] Verify site renders correctly at localhost
- [ ] Check recipe pages display properly
- [ ] Test search with Fuse.js
- [ ] Verify asset URLs work with /CookBook/ prefix
- [ ] Check responsive design and DaisyUI components
- [ ] Test Python scripts in scripts/ directory (if upgrading Python packages)
- [ ] Verify Decap CMS admin interface works

### Rollback Plan
If issues occur:
1. **For npm**: Revert package.json to previous versions, run `npm install`
2. **For Hugo**: Reinstall previous Hugo version
3. **For config files**: Revert changes to hugo.toml, tailwind.config.js, etc.
4. Revert code changes from this upgrade
```

### Step 6: Apply changes

Implement changes in this order:

1. **Update package.json** with new version (for npm packages)
2. **Install packages**: `npm install`
3. **Apply required code changes** from Step 3
4. **Update configuration files** if needed (hugo.toml, tailwind.config.js)
5. **Optionally implement new features** from Step 4

Use multi_replace_string_in_file for multiple changes across files.

### Step 7: Verify functionality

Run comprehensive verification:

```bash
# Build the site
npm run build

# Run search tests
npm run test:search:v7

# Start dev server and manually test
hugo server -D

# Check for syntax errors in templates
hugo --renderToMemory

# Test Python scripts (if applicable)
python scripts/list_tags.py
python scripts/find_recipes_with_tag.py --tag "desired-tag"
```

**IMPORTANT**: If verification fails:
1. Review error messages carefully
2. Check if additional breaking changes were missed
3. Consult Context7 MCP server for additional documentation
4. Consider rolling back if issues cannot be resolved quickly

## Common package categories

### Hugo (static site generator)
- Check template syntax changes (Go templates)
- Verify shortcode compatibility
- Test content rendering and frontmatter parsing
- Review asset pipeline changes (Hugo Pipes)
- Check taxonomy and menu handling
- Verify multilingual support (i18n)

### Tailwind CSS & DaisyUI
- Check class name changes or deprecations
- Verify component markup compatibility
- Test responsive utilities
- Review configuration format changes (tailwind.config.js)
- Check PostCSS integration
- Verify theme customization works

### Fuse.js (search library)
- Check search algorithm changes
- Verify options/configuration format
- Test search accuracy and performance
- Review threshold and scoring changes
- Check index format compatibility

### npm build tools (@tailwindcss/cli, postcss, autoprefixer)
- Check CLI argument changes
- Verify build script compatibility
- Test asset processing pipeline
- Review output format changes

### Python utility packages (used in scripts/)
- Check import path changes
- Verify CLI argument parsing (argparse)
- Test file I/O operations
- Review YAML/JSON parsing libraries

## Project-specific considerations

This application has these key characteristics:

**Deployment**: GitHub Pages (static site hosting)
- Site served under /CookBook/ path prefix
- Must use `asset-url.html` partial for all asset URLs
- Cache-busting via query parameters
- Static HTML generation, no server-side processing

**Critical paths**:
1. Recipe content rendering (layouts/_default/single.html, layouts/partials/summary.html)
2. Search functionality (layouts/index.json, static/js/ with Fuse.js)
3. Recipe card display and filtering (layouts/index.html)
4. Asset processing (Tailwind CSS compilation from assets/css/main.css)
5. Python recipe management scripts (scripts/*.py)

**Critical features**:
- FODMAP diet filtering and badges
- Recipe search with fuzzy matching
- Responsive recipe cards with square images
- Video modal integration (YouTube embeds)
- Recipe rating and macro display
- Decap CMS content editing

When upgrading packages used in these areas, prioritize stability and visual consistency over new features.

## Package-specific guidance

See [PACKAGE_NOTES.md](PACKAGE_NOTES.md) for version-specific upgrade notes.

## Troubleshooting

### Error: Import fails after upgrade
1. Check if package structure changed
2. Verify submodule imports (especially for ES modules vs CommonJS)
3. Check for renamed modules or moved files
4. Review deprecation warnings in build output
5. For Hugo: Check template function changes

### Error: Build fails after upgrade
1. Check build command compatibility (`npm run build`)
2. Verify PostCSS/Tailwind configuration
3. Check for Hugo template syntax errors
4. Review asset pipeline changes
5. Test with `--verbose` flag for detailed output

### Error: Styles not applying after Tailwind/DaisyUI upgrade
1. Check class name changes in components
2. Verify tailwind.config.js configuration format
3. Review DaisyUI theme customization
4. Check if CSS is being properly generated
5. Clear Hugo resources cache: `rm -rf resources/_gen`

### Error: Search not working after Fuse.js upgrade
1. Check Fuse.js options format changes
2. Verify search index structure (layouts/index.json)
3. Test search threshold values
4. Review key/field name changes
5. Check JavaScript console for errors

## Best practices

✓ **Always read the full changelog** between versions, not just latest
✓ **Test in local environment** before committing changes
✓ **Update one package at a time** to isolate issues
✓ **Check transitive dependencies** that might also upgrade
✓ **Review security advisories** for the package
✓ **Document why upgrade is needed** in commit message

✗ **Don't skip testing** even for "minor" version bumps
✗ **Don't upgrade multiple packages simultaneously**
✗ **Don't ignore deprecation warnings**
✗ **Don't assume semantic versioning** is strictly followed

## Output format

After completing the upgrade analysis, provide:

```markdown
# Package Upgrade Summary: <package_name>

## Current Status
- Current version: v<current>
- Target version: v<target>
- Risk level: [Low/Medium/High]

## Required Changes
[List all required code changes with file paths and line numbers]

## Optional Improvements
[List beneficial new features to consider]

## Files Affected
- path/to/file1.py (3 changes)
- path/to/file2.py (1 change)

## Next Steps
1. [Specific action]
2. [Specific action]

## Estimated Time
- Required changes: [X] minutes
- Optional improvements: [Y] minutes
- Testing: [Z] minutes
```

---
name: smith-ide
description: IDE path variable mappings for VS Code, Cursor, Kiro, and JetBrains. Use when writing or editing IDE config files or using path variables. Covers variable translation between conceptual and IDE-specific syntax.
---

# IDE Path Variable Mappings

<metadata>

- **Scope**: Maps conceptual path variables to IDE-specific syntax
- **Load if**: Writing/editing IDE config files (.vscode/, .kiro/, .cursor/) OR using IDE path variables
- **Prerequisites**: @smith-principles/SKILL.md, @smith-standards/SKILL.md, `@smith-style/SKILL.md`

</metadata>

## CRITICAL: Variable Translation (Primacy Zone)

<required>

**Always use conceptual variables in documentation**, translate to IDE-specific syntax in configs:
- `$WORKSPACE_ROOT` → `${workspaceFolder}` (VS Code) or `$PROJECT_DIR$` (JetBrains)
- `$HOME` → `${userHome}` (VS Code) or `$USER_HOME$` (JetBrains)

</required>

<context>

## Overview

Maps conceptual path variables to IDE-specific syntax. For variable definitions and usage, see `@smith-style/SKILL.md#path-references`.

## Conceptual Variables

**Defined in**: `@smith-style/SKILL.md#path-references`

For path variable definitions (`$WORKSPACE_ROOT`, `$REPO_ROOT`, `$HOME`) and usage patterns, see `@smith-style/SKILL.md#path-references`.

</context>

## IDE Syntax Mappings

### VS Code-Based IDEs (VS Code, Cursor, Kiro)

**Syntax**: `${variableName}`

**Common Variables**:
- `${workspaceFolder}` — Workspace root directory
- `${userHome}` — User home directory
- `${env:VAR}` — Environment variable
- `${config:key}` — Settings value

**Mappings**:
- `$WORKSPACE_ROOT` → `${workspaceFolder}`
- `$REPO_ROOT` → `${env:REPO_ROOT}` or `${workspaceFolder}/../../../../`
- `$HOME` → `${userHome}`

**Multi-root workspaces**: Use `${workspaceFolder:folderName}` for specific folders

**Configuration**:
- **VS Code/Cursor**: `.vscode/settings.json`
- **Kiro**: `.kiro/settings/mcp.json` (workspace) or `~/.kiro/settings/mcp.json` (global)

**Note**: Kiro is VS Code-based (Code OSS fork) and inherits VS Code configuration system.

### JetBrains IDEs (PyCharm, IntelliJ IDEA)

**Syntax**: `$MACRO_NAME$`

**Common Macros**:
- `$PROJECT_DIR$` — Project root directory
- `$USER_HOME$` — User home directory

**Mappings**:
- `$WORKSPACE_ROOT` → `$PROJECT_DIR$`
- `$REPO_ROOT` → `$PROJECT_DIR$/../../../../` (or custom path variable)
- `$HOME` → `$USER_HOME$`

**Configuration**: File → Settings → Appearance & Behavior → Path Variables

<required>

## Best Practices

1. **Documentation**: Always use conceptual variables (`$WORKSPACE_ROOT`, `$REPO_ROOT`, `$HOME`)
2. **IDE Configs**: Translate to IDE-specific syntax using above mappings
3. **Cross-IDE Compatibility**: Prefer environment variables when possible
4. **Security**: Use variable references for sensitive values, never hardcode

</required>

## Reference

<related>

- **VS Code Variables**: [Documentation](https://code.visualstudio.com/docs/editor/variables-reference)
- **PyCharm Macros**: [Documentation](https://www.jetbrains.com/help/idea/absolute-path-variables.html)
- **Path Standards**: `@smith-style/SKILL.md#path-references`

</related>

## ACTION (Recency Zone)

<required>

**When writing IDE configs:**
1. Use conceptual variables in docs (`$WORKSPACE_ROOT`)
2. Translate to IDE syntax in config files
3. Prefer environment variables for cross-IDE compatibility

</required>

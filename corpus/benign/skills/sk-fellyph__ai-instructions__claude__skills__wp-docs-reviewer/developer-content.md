# Developer Content Guidelines

Detailed reference for reviewing code examples, placeholders, command-line syntax, and UI elements in WordPress documentation.

## Table of Contents

1. [Code in Text](#code-in-text)
2. [Code Examples](#code-examples)
3. [Placeholders](#placeholders)
4. [Command-line Syntax](#command-line-syntax)
5. [UI Elements](#ui-elements)
6. [Coding Standards](#coding-standards)

## Code in Text

### Items to Put in Code Font

Use monospace code font (in HTML: `<code>`, in Markdown: backticks) for:
- Attribute names and values
- Class names
- Command-line utility names
- Data types
- Element names (with angle brackets: `<div>`)
- Filenames, extensions, and paths
- Folders and directories
- HTTP verbs, status codes, content-type values
- Language keywords
- Method and function names (with parentheses: `get_option()`)
- Namespace aliases
- Placeholder variables
- Query parameter names and values
- Text input
- UI elements implementing user-entered text

### Items NOT in Code Font

Use regular font for:
- Email addresses
- Product/service/organization names (unless also a command-line utility)
- URLs (but do link them)

### Method Names Format

**Correct**: `delete()` method
**Incorrect**: `WP_Filesystem_ftpsockets::delete()` method (unless ambiguous)

Always include empty parentheses to indicate it's a method.

### HTTP Status Codes

**Single code**: an HTTP `500 Internal Server Error` status code
**Range with X**: an HTTP `2xx` or `300` status code
**Specific range**: an HTTP status code in the `200`-`299` range

## Code Examples

### General Guidelines

- Use spaces for indentation (not tabs)
- Follow WordPress Coding Standards indentation
- Wrap lines at 80 characters
- Mark code blocks properly:
  - HTML: `<pre>` element
  - Markdown: code fence (` ``` `)

### Introductory Sentences

**With period**: Extended intro with additional context
```
The following shows the post method. For more info, see the Code Reference.

[code example]
```

**With colon**: Short, immediate intro
```
Use the post method:

[code example]
```

**No partial statements**: Must be complete sentence before colon

**Incorrect**: The following shows:
**Correct**: The following example shows the delete method:

## Placeholders

### Format Requirements

**In inline text (HTML)**:
```html
<code><var>PLACEHOLDER_VARIABLE</var></code>
```

**In inline text (Markdown)**:
```markdown
*`PLACEHOLDER_VARIABLE`*
```

**In code blocks (HTML)**:
```html
<pre class="prototype">
<img src="<var>IMAGE_PATH</var>" alt="<var>ALT_TEXT</var>" />
</pre>
```

**In code blocks (Markdown)**:
Cannot apply formatting inside code fence

### Naming Conventions

**Correct**:
- `API_NAME`
- `POST_TITLE`
- `IMAGE_PATH`

**Incorrect**:
- `API-name` (mixed case/hyphens)
- `API name` (spaces)
- `api_name` (lowercase)
- `apiName` (camelCase)
- `MY_API_NAME` (possessive pronoun)
- `YOUR_API_NAME` (possessive pronoun)

### Describing Placeholders

**Single placeholder**:
```
Replace <var>POST_ID</var> with the ID of the post.
```

**Multiple placeholders**:
```
Replace the following:
- <var>POST_ID</var>: the ID of the post.
- <var>PATH</var>: the path to WordPress files.
- <var>THEMES</var>: comma-separated list of themes.
```

**Placeholders in output**:
```
In this output:
- <var>SITE_NAME</var>: the name of the site.
- <var>VERSION</var>: the version number.
```

## Command-line Syntax

### Command Prompt

- Use dollar sign (`$`) for command prompt
- Don't show directory paths before prompt
- Use separate code blocks for input and output

**Example**:
```shell
$ wp theme activate twentytwentyone
```
Output:
```
Success: Switched to 'Twenty Twenty-One' theme.
```

### Required vs Optional Arguments

**Required** (no brackets):
```shell
$ wp post list --post_type='page'
```

**Optional** (square brackets, separate for each):
```shell
$ wp plugin install <url> [--force] [--activate]
```

### Mutually Exclusive Arguments

Use angle brackets with pipes:
```shell
$ wp plugin install <plugin|zip|url>
```

### Multiple Value Arguments

Use ellipsis:
```shell
$ wp media import [--post_id=<post_id>...]
$ wp plugin install <plugin|zip|url>...
```

### Command Output

Only show output when useful (for copying values or verification).

**Introductory phrases**:
- "The output is the following:"
- "The output is similar to the following:"

### Line Breaks in Commands

When line exceeds 100 characters:
- Break before: hyphen, underscore, quotes
- Indent continuation lines by 4 spaces
- End each line (except last) with continuation character:
  - Linux/shell: space + backslash (` \`)
  - Windows: space + caret (` ^`)

## UI Elements

### Formatting

**Bold for UI element names**: **Settings** > **Reading**

### Interaction Verbs

**Task-focused** (preferred):
- "Select **Settings**"
- "Go to **Tools** > **Import**"
- "In the **Title** field, enter the post title"

**Avoid** (when possible):
- "Click **Settings**"
- "Type in the Title box"
- "Touch **Save**"

### Element Terminology

Use correct terms:
- Button
- Menu
- Field
- Tab
- Dialog
- Checkbox
- Radio button
- Dropdown (or drop-down list)
- Text box
- Link

### Capitalization

Match the exact capitalization from the UI:
- **Publish** (not **publish**)
- **Add New** (not **Add new**)

## Coding Standards

All code examples must follow [WordPress Coding Standards](https://developer.wordpress.org/coding-standards/):

### PHP Standards
- Function names: lowercase, underscores
- Class names: PascalCase
- Constants: UPPERCASE_UNDERSCORES
- Brace style: Allman for functions/classes, K&R for control structures
- Indentation: Tabs (width of 4 spaces)
- Yoda conditions: `if ( true === $condition )`

### JavaScript Standards
- Use strict equality: `===` and `!==`
- Semicolons required
- Single quotes for strings
- camelCase for variables and functions

### CSS Standards
- Lowercase selectors
- Hyphenated properties
- Space after colon
- Properties on separate lines

### Accessibility Standards
- Use semantic HTML elements
- Include ARIA labels where needed
- Ensure keyboard navigation works
- Provide text alternatives for media

## Common Mistakes to Flag

1. **Using curly quotes instead of straight quotes**
   - Wrong: "Hello" or 'World'
   - Correct: "Hello" or 'World'

2. **Missing empty parentheses on method names**
   - Wrong: the `delete` method
   - Correct: the `delete()` method

3. **Using keywords as verbs**
   - Wrong: "Decompress the body"
   - Correct: "Decompress the body using a `decompress` request"

4. **Inconsistent placeholder formatting**
   - Must be: UPPERCASE_UNDERSCORE format
   - No possessives: MY_, YOUR_

5. **Missing introductory sentences for code blocks**
   - Every code example needs context

6. **Not following WordPress Coding Standards**
   - Check indentation, naming, and style

7. **Command prompt inconsistencies**
   - Always use `$` for shell commands
   - Separate input from output

8. **Unclear UI instructions**
   - Use bold for UI elements
   - Use task-focused verbs

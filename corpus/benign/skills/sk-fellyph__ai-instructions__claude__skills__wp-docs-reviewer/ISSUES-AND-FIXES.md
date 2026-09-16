# Example Documentation Issues and Fixes

This guide explains the issues found in `problematic-documentation.md` and how they were corrected in `corrected-documentation.md`.

## Critical Issues

### 1. Non-inclusive Terminology

**Issue**: Used "master branch" and "whitelist"
```markdown
# Problematic
...using the master branch...
The whitelist of approved contributors...
```

**Fix**: Changed to "main branch" and "allowlist"
```markdown
# Corrected
...using the main branch...
The allowlist of approved contributors...
```

**Why**: WordPress style guide requires inclusive terminology to avoid terms with negative historical connotations.

### 2. Ableist Language

**Issue**: "The disabled users might have trouble"
```markdown
# Problematic
The disabled users might have trouble with some features
```

**Fix**: Removed the statement (or could be rewritten as "The plugin is accessible to people with disabilities")
```markdown
# Corrected
[Statement removed or rewritten to focus on accessibility features]
```

**Why**: Use person-first language: "people with disabilities" not "disabled users"

### 3. Missing Alt Text

**Issue**: Image with no descriptive alt text
```markdown
# Problematic
![Dashboard](screenshot.png)
```

**Fix**: Added descriptive alt text under 50 characters
```markdown
# Corrected
![Plugin dashboard showing main settings](screenshot.png)
```

**Why**: Alt text is critical for accessibility and should describe what's shown in the image

## Important Issues

### 4. Use of "We"

**Issue**: "We recommend installing..."
```markdown
# Problematic
We recommend installing the plugin from the WordPress repository.
```

**Fix**: Direct second-person address
```markdown
# Corrected
You can install the plugin from the WordPress repository.
```

**Why**: WordPress style guide avoids "we" statements; use second person instead

### 5. Gendered Language

**Issue**: "You guys can easily install"
```markdown
# Problematic
You guys can easily install it...
```

**Fix**: Gender-neutral language
```markdown
# Corrected
You can install the plugin...
```

**Why**: "Guys" is gendered; use "you", "everyone", "folks", or "people"

### 6. Passive Voice

**Issue**: "The plugin will be installed when you click"
```markdown
# Problematic
The plugin will be installed when you click the install button
```

**Fix**: Active voice with direct instruction
```markdown
# Corrected
Select **Install Now**.
```

**Why**: Active voice is clearer and more direct

### 7. Inconsistent UI Element Capitalization

**Issue**: Lowercase UI elements that should match interface
```markdown
# Problematic
Click on **plugins** in the left sidebar
Click **add new**
```

**Fix**: Proper capitalization matching the actual UI
```markdown
# Corrected
Select **Plugins** in the left sidebar.
Select **Add New**.
```

**Why**: UI elements should match exact capitalization from the interface

### 8. Click-Focused Instructions

**Issue**: "Click" used for all interactions
```markdown
# Problematic
Click on **plugins**
Click **add new**
Please click **activate**
```

**Fix**: Task-focused verbs
```markdown
# Corrected
Select **Plugins**
Select **Add New**
Select **Activate**
```

**Why**: "Select" is more inclusive of different input methods (touch, keyboard, voice)

### 9. Directional-Only Instructions

**Issue**: "on the right side of your dashboard"
```markdown
# Problematic
...on the right side of your dashboard
```

**Fix**: Removed directional reference or added specific path
```markdown
# Corrected
To configure the plugin settings, go to **Settings** > **Plugin Settings**.
```

**Why**: Screen layouts vary; use specific paths instead of directions

### 10. Placeholder Formatting

**Issue**: Possessive pronoun in placeholder
```markdown
# Problematic
paste YOUR_API_KEY into the field
```

**Fix**: Non-possessive placeholder with formatting
```markdown
# Corrected
define( 'API_KEY', *`API_KEY`* );

Replace *`API_KEY`* with your actual API key.
```

**Why**: No possessive pronouns (MY_, YOUR_); use proper placeholder formatting

### 11. Informal Language

**Issue**: "crazy useful"
```markdown
# Problematic
The plugin has many advanced options that are crazy useful!
```

**Fix**: Professional, descriptive language
```markdown
# Corrected
The plugin provides several advanced features:
```

**Why**: Avoid slang and overly casual language

### 12. Excessive Claims

**Issue**: Superlative claims without basis
```markdown
# Problematic
- This plugin is awesome!
- It's better than all the other plugins
```

**Fix**: Factual statements
```markdown
# Corrected
- The plugin integrates with popular caching solutions
- Compatible with WordPress 6.0 and higher
```

**Why**: Avoid excessive or unsubstantiated claims

### 13. Future Predictions

**Issue**: "we will add many new features"
```markdown
# Problematic
In the future, we will add many new features
```

**Fix**: Statement removed
```markdown
# Corrected
[Future predictions removed]
```

**Why**: Don't document or predict future features

### 14. Poor Link Text

**Issue**: "click here" and bare URLs
```markdown
# Problematic
click here to visit our support forum: https://example.com/support
For more info, see our website.
```

**Fix**: Descriptive link text
```markdown
# Corrected
For support questions, visit the [support forum](https://example.com/support).
For additional information, see the [plugin website](https://example.com).
```

**Why**: Link text should be descriptive and meaningful

### 15. Conditional Clause Placement

**Issue**: Condition after instruction
```markdown
# Problematic
You must have administrator access to install plugins.
```

**Fix**: Condition before instruction (or as note after)
```markdown
# Corrected
**Note**: You need administrator access to install plugins.
```

**Why**: Conditions should come before instructions when possible

### 16. Inadequate Code Introduction

**Issue**: No introductory sentence
```markdown
# Problematic
Here's how to use the main function:

```php
[code]
```
```

**Fix**: Clear introductory sentence
```markdown
# Corrected
The following example shows how to use the `process_data()` function:

```php
[code]
```
```

**Why**: Code examples should have clear introductory context

### 17. Vague Troubleshooting

**Issue**: Unclear instructions
```markdown
# Problematic
**Problem**: The plugin is not working
Solution: Make sure you activated it correctly
```

**Fix**: Specific, numbered steps
```markdown
# Corrected
### Plugin not working

If the plugin doesn't work after activation:

1. Verify the plugin activated successfully in **Plugins**.
2. Check for PHP error messages in debug logs.
3. Ensure your WordPress version meets the minimum requirements.
```

**Why**: Troubleshooting needs specific, actionable steps

### 18. Heading Capitalization

**Issue**: Title case in subheadings
```markdown
# Problematic
## Installing the Plugin
## API Settings
```

**Fix**: Sentence case
```markdown
# Corrected
## Installing the plugin
## API settings
```

**Why**: Use sentence case for all headings

### 19. Inconsistent List Format

**Issue**: Mixed formats and missing parallel structure
```markdown
# Problematic
- Caching (This will improve performance)
- Logging (useful for debugging)
- Auto-updates (the plugin will update automatically)
```

**Fix**: Parallel structure with consistent descriptions
```markdown
# Corrected
- **Caching**: Improves performance by storing frequently accessed data
- **Logging**: Records events for troubleshooting
- **Auto-updates**: Keeps the plugin current automatically
```

**Why**: Lists should have parallel structure and consistent formatting

### 20. Excessive Exclamation Points

**Issue**: Overuse of exclamation points
```markdown
# Problematic
The plugin has many advanced options that are crazy useful!
```

**Fix**: Removed unnecessary exclamation points
```markdown
# Corrected
The plugin provides several advanced features:
```

**Why**: Use exclamation points sparingly, if at all

## Summary Statistics

**Total issues found**: 20
- **Critical**: 3 (non-inclusive terminology, ableist language, missing alt text)
- **Important**: 17 (voice, tone, formatting, clarity issues)

**Categories**:
- Inclusivity: 3 issues
- Voice/Tone: 5 issues
- Accessibility: 2 issues
- Code/Technical: 3 issues
- Formatting: 5 issues
- Content: 2 issues

This demonstrates the comprehensive nature of WordPress documentation standards and the importance of systematic review.

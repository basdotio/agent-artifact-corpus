# Quick Start Guide

Get up and running with the WordPress Documentation Review Skill in 5 minutes.

## Installation

1. **Download the skill files** to your local machine

2. **Create the skill directory**:
   ```bash
   mkdir -p wordpress-docs-review/references
   ```

3. **Copy the files**:
   - Copy `SKILL.md` to `wordpress-docs-review/`
   - Copy `developer-content.md` and `style-guidelines.md` to `wordpress-docs-review/references/`

4. **Upload to Claude** (if using Claude.ai) or configure in your environment

## First Review

Try the skill with the provided examples:

1. **Test with problematic documentation**:
   ```
   Review this WordPress documentation for style guide compliance.
   [Upload examples/problematic-documentation.md]
   ```

2. **Compare with corrected version**:
   ```
   Now review this corrected version and confirm it meets standards.
   [Upload examples/corrected-documentation.md]
   ```

3. **See detailed explanations**:
   ```
   Show me the specific issues in the problematic version.
   [Reference examples/ISSUES-AND-FIXES.md]
   ```

## Common Use Cases

### Use Case 1: Pre-Publication Review
```
I'm about to publish this plugin documentation. Please review it against 
WordPress standards and prioritize any critical issues.

[Upload your documentation]
```

### Use Case 2: PR Feedback
```
This is a pull request for updating developer documentation. Review it 
focusing on code examples and placeholder formatting.

[Upload PR content]
```

### Use Case 3: Bulk Audit
```
I need to audit all our documentation. Start with this page and identify 
the most common issues across sections.

[Upload documentation]
```

### Use Case 4: Specific Section Review
```
Check just the "Installation" and "Configuration" sections for 
accessibility and inclusivity issues.

[Upload documentation]
```

## What to Expect

The skill will provide:

1. **Summary**: Overview of documentation quality
2. **Critical Issues**: Must-fix items (accessibility, inclusivity, technical accuracy)
3. **Important Issues**: Should-fix items (voice, tone, formatting)
4. **Suggestions**: Nice-to-have improvements
5. **Positive Highlights**: What works well
6. **Overall Assessment**: Readiness for publication

## Review Categories

The skill checks:

- ✓ **General Guidelines**: Structure, voice, tone, accessibility, inclusivity
- ✓ **Language & Grammar**: Active voice, present tense, capitalization
- ✓ **Developer Content**: Code formatting, placeholders, CLI syntax
- ✓ **Punctuation**: Commas, quotes, dashes
- ✓ **Formatting**: Links, lists, media, tables

## Tips for Best Results

### 1. Provide Context
```
This is end-user documentation for a beginner-friendly plugin.
[Documentation]
```

### 2. Specify Focus Areas
```
Focus on code examples and command-line syntax in this developer guide.
[Documentation]
```

### 3. Ask for Examples
```
For each issue, show me the incorrect version and the corrected version.
[Documentation]
```

### 4. Request Prioritization
```
We're on a tight deadline. What are the absolute must-fix issues?
[Documentation]
```

## Understanding Feedback

### Critical Issues (Red Flag 🚨)
Must be fixed before publication:
- Accessibility violations
- Non-inclusive language
- Incorrect technical information
- Code that violates WordPress standards

### Important Issues (Yellow Flag ⚠️)
Should be fixed for quality:
- Voice/tone inconsistencies
- Formatting problems
- Unclear instructions
- Missing descriptions

### Suggestions (Blue Flag 💡)
Nice to have:
- Style improvements
- Additional examples
- Enhanced clarity

## After Your Review

1. **Fix critical issues** immediately
2. **Address important issues** before publication
3. **Consider suggestions** for continuous improvement
4. **Learn patterns** to improve future documentation
5. **Re-review** if major changes were made

## Troubleshooting

### "The skill isn't triggering"
Make sure you mention:
- "WordPress documentation"
- "Review" or "check" or "audit"
- Style guide compliance

### "Feedback is too general"
Ask for:
- Specific line numbers
- Before/after examples
- Style guide references

### "Too many issues to fix"
Request:
- "Prioritize by impact"
- "Show me the top 5 issues"
- "What blocks publication?"

## Learning Resources

- [WordPress Documentation Style Guide](https://make.wordpress.org/docs/style-guide/)
- [WordPress Coding Standards](https://developer.wordpress.org/coding-standards/)
- [Documentation Contributor Handbook](https://make.wordpress.org/docs/handbook/)

## Examples Directory

The `examples/` directory contains:

1. **problematic-documentation.md**: Documentation with 20+ common issues
2. **corrected-documentation.md**: Same documentation, properly fixed
3. **ISSUES-AND-FIXES.md**: Detailed explanation of each issue and fix

Use these to:
- Learn what the skill catches
- Understand WordPress standards
- Test the skill functionality
- Train team members

## Next Steps

1. Review the examples to understand common issues
2. Try reviewing your own documentation
3. Learn from the feedback patterns
4. Improve your documentation process
5. Contribute improvements to the skill

## Support

- Check [README.md](README.md) for detailed information
- See [CONTRIBUTING.md](CONTRIBUTING.md) to improve the skill
- Review reference files for specific guidelines
- Join #docs on WordPress Slack

---

**Ready to start?** Upload your first documentation file and ask for a review!

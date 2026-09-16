# WordPress Documentation Review Skill

A comprehensive skill for reviewing WordPress documentation against official style guide standards.

## Directory Structure

```
wordpress-docs-review/
├── SKILL.md                              # Main skill file with review process
└── references/
    ├── developer-content.md              # Code examples, placeholders, CLI syntax
    └── style-guidelines.md               # Voice, tone, accessibility, inclusivity
```

## Installation

1. Create a directory named `wordpress-docs-review` in your skills folder
2. Copy `SKILL.md` to the root of that directory
3. Create a `references/` subdirectory
4. Copy both reference files into the `references/` subdirectory

## What This Skill Does

This skill provides systematic review of WordPress documentation, checking:

- **General Guidelines**: Document structure, voice/tone, accessibility, inclusivity, global audience
- **Language & Grammar**: Active voice, present tense, second person, capitalization
- **Developer Content**: Code formatting, placeholders, command-line syntax, UI elements
- **Punctuation**: Serial commas, straight quotes, proper dash usage
- **Formatting**: Links, lists, media, tables

## How It Works

### Automatic Triggering

The skill triggers when you:
- Ask to review WordPress documentation
- Request feedback on documentation pull requests
- Check documentation for style guide compliance
- Audit existing documentation

### Review Process

1. **Identifies documentation type** (end-user, developer, tutorial, code reference)
2. **Performs systematic review** using comprehensive checklists
3. **Categorizes issues** by priority:
   - Critical (must fix before publication)
   - Important (should fix)
   - Suggestions (nice to have)
4. **Generates structured output** with specific locations and fixes

### Output Format

Reviews include:
- Summary of documentation quality
- Critical issues with fixes
- Important issues with fixes
- Suggestions for improvement
- Positive highlights
- Overall assessment

## Key Features

### Comprehensive Checklists

- 50+ review criteria across all documentation aspects
- Organized by category for systematic review
- Based on official WordPress Documentation Style Guide

### Detailed References

- **developer-content.md**: 
  - Code in text formatting
  - Code example standards
  - Placeholder conventions
  - Command-line syntax
  - UI element guidelines
  - WordPress Coding Standards

- **style-guidelines.md**:
  - Voice and tone principles
  - Accessibility requirements
  - Inclusivity standards
  - Global audience considerations
  - Document structure
  - Facts and claims verification

### Terminology Reference

Built-in reference for preferred WordPress terminology:
- allowlist (not whitelist)
- blocklist (not blacklist)
- main branch (not master)
- primary/subordinate (not master/slave)
- person with disability (not disabled person)

## Usage Examples

### Example 1: Review Documentation File
```
Review this WordPress plugin documentation against the style guide.
[attach documentation file]
```

### Example 2: Check Specific Aspects
```
Check this developer documentation for code formatting and placeholder usage.
[attach documentation]
```

### Example 3: Pre-Publication Review
```
I'm about to publish this tutorial. Can you review it for WordPress documentation standards?
[attach tutorial]
```

## Best Practices

1. **Be Specific**: The skill will point to exact locations with fixes
2. **Prioritize**: Focus on critical and important issues first
3. **Learn**: Use feedback to understand style guide principles
4. **Iterate**: Apply learnings to improve documentation quality

## Style Guide References

This skill is based on:
- [WordPress Documentation Style Guide](https://make.wordpress.org/docs/style-guide/)
- [WordPress Coding Standards](https://developer.wordpress.org/coding-standards/)
- [WordPress Documentation Team Handbook](https://make.wordpress.org/docs/handbook/)

## Contributing

To improve this skill:
1. Test with real WordPress documentation
2. Note any gaps or inaccuracies
3. Update SKILL.md or reference files as needed
4. Submit improvements via pull request

## License

MIT License - See individual files for complete terms.

## Version

1.0.0 - Initial release

## Support

For questions about this skill:
- Check the reference files for detailed guidelines
- Consult the WordPress Documentation Style Guide
- Join #docs channel on WordPress Slack

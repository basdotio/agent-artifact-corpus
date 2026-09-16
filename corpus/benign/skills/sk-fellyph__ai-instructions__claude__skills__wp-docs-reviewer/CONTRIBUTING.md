# Contributing to WordPress Documentation Review Skill

Thank you for your interest in improving the WordPress Documentation Review Skill! This guide will help you contribute effectively.

## How to Contribute

### Reporting Issues

If you find errors or gaps in the skill:

1. **Check existing issues** to avoid duplicates
2. **Provide specific examples** of documentation that wasn't reviewed correctly
3. **Include expected vs. actual behavior**
4. **Reference WordPress Style Guide** sections if applicable

### Improving the Skill

You can contribute by:

1. **Adding missing guidelines** from the WordPress Style Guide
2. **Improving checklists** with more specific criteria
3. **Adding examples** to reference files
4. **Fixing errors** in the review process
5. **Enhancing clarity** of instructions

## Development Workflow

### 1. Testing the Skill

Before making changes:
- Test with various WordPress documentation types
- Note what works well and what doesn't
- Identify specific improvements needed

### 2. Making Changes

#### SKILL.md Changes
- Keep the review process clear and actionable
- Maintain the 4-step structure
- Add checklist items where appropriate
- Update reference file links if adding new files

#### Reference File Changes
- Add detailed examples
- Keep formatting consistent
- Include both correct and incorrect examples
- Organize content logically

### 3. Testing Your Changes

After making changes:
- Test with real WordPress documentation
- Verify the skill triggers appropriately
- Check that feedback is actionable
- Ensure no regressions in existing functionality

### 4. Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/improve-accessibility-checks`
3. Make your changes
4. Test thoroughly
5. Commit with clear messages: `git commit -m "Add color contrast checking to accessibility review"`
6. Push to your fork: `git push origin feature/improve-accessibility-checks`
7. Open a pull request

## Skill Structure Guidelines

### SKILL.md Best Practices

- **Keep it under 500 lines** - Move detailed content to reference files
- **Use progressive disclosure** - Basic info in SKILL.md, details in references
- **Make checklists scannable** - Use clear, actionable items
- **Reference external files** - Point to reference files for deep dives

### Reference Files Best Practices

- **Include table of contents** for files over 100 lines
- **Provide examples** for each guideline
- **Show correct and incorrect** versions side-by-side
- **Organize by topic** for easy navigation
- **Cross-reference** between files when needed

## Style Conventions

### Markdown Formatting

- Use `**bold**` for emphasis
- Use `*italics*` for terminology
- Use `` `code` `` for technical terms
- Use `---` for section dividers
- Use `###` for subsections

### Code Examples

```markdown
**Correct**:
```
[good example]
```

**Incorrect**:
```
[bad example]
```
```

### Checklists

```markdown
- [ ] Item uses imperative mood
- [ ] Item is specific and measurable
- [ ] Item references style guide when helpful
```

## Areas Needing Contribution

Current priorities:

1. **Examples Library**: Add more real-world examples
2. **Edge Cases**: Document how to handle ambiguous situations
3. **Automation**: Identify patterns that could be automated
4. **Translations**: Consider multilingual documentation reviews
5. **WordPress 6.x Updates**: Keep pace with new WordPress features

## Questions?

- Check the [README](README.md) for skill overview
- Review the [WordPress Style Guide](https://make.wordpress.org/docs/style-guide/)
- Ask in WordPress #docs Slack channel
- Open a discussion issue

## Code of Conduct

Follow the [WordPress Code of Conduct](https://make.wordpress.org/handbook/community-code-of-conduct/):

- Be respectful and welcoming
- Be collaborative
- Be considerate
- Be patient with new contributors

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be acknowledged in:
- Repository contributors list
- Release notes for significant contributions
- README acknowledgments section

Thank you for helping improve WordPress documentation quality!

# Mermaid Standards Skill

This skill provides standardized conventions for creating Mermaid diagrams in technical design documents.

---

## When to Use This Skill

Claude will automatically reference this skill when:
- Generating technical design documents (`/generate-design`)
- Creating architecture visualizations
- Documenting system flows and interactions
- Drawing class structures or entity relationships

---

## Contents

All diagram standards are documented in `diagram-conventions.md`:
- Default theme configuration (Mermaid's built-in default)
- Class diagram conventions
- Sequence diagram conventions
- Flowchart conventions for activity/workflow diagrams
- Complete working examples for each diagram type

---

## Design Principles

- **Consistency**: All diagrams use the same syntax patterns and Mermaid default theme
- **Clarity**: Stereotypes (`<<new>>`, `<<modified>>`, `<<existing>>`) show change impact
- **Completeness**: Diagrams include both happy paths and error handling
- **Readability**: Keep diagrams focused and not overly complex
- **Native Support**: Mermaid renders natively in GitHub, GitLab, and most markdown viewers

---

## How to Apply These Standards

When generating design documents:
1. Reference this skill for all Mermaid diagram generation
2. Use Mermaid's default theme (no custom configuration needed)
3. Use appropriate diagram types based on what you're documenting:
   - **Class diagrams**: Show component structure and relationships
   - **Sequence diagrams**: Show request flows and interactions
   - **Flowcharts**: Show complex business logic and decision points
4. Always include error handling paths in sequence and flowchart diagrams
5. Use stereotypes to clearly indicate which components are new, modified, or existing

---

## Advantages of Mermaid

- **Native Rendering**: GitHub, GitLab, and many tools render Mermaid diagrams directly
- **Simple Syntax**: Easier to read and write than PlantUML
- **No Dependencies**: No need for external rendering engines
- **Live Diagrams**: View diagrams directly in markdown without image generation
- **Version Control**: Diagrams are text-based and diff-friendly

---

## Extensibility

This skill can be extended in the future with:
- Entity-Relationship Diagrams (ERD) for database design
- State diagrams for lifecycle management
- Gantt charts for project planning
- Pie charts for data visualization
- Git graphs for branch visualization

---

**For detailed conventions and examples, see `diagram-conventions.md`**

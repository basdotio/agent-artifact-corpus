---
name: mermaid-diagrams
description: Generate syntactically correct Mermaid diagrams. Use when creating flowcharts, sequence diagrams, state diagrams, ERDs, class diagrams, or any visual diagram in Mermaid format.
---

# Mermaid Diagram Generation

When generating Mermaid diagrams, follow these rules to ensure valid syntax.

## Universal Rules

1. **Avoid special characters in labels** - Characters like `::`, `<`, `>`, `|`, `{`, `}` often have special meaning
2. **Quote labels with spaces** - Use quotes around labels containing spaces: `A["My Label"]`
3. **No empty lines inside diagram blocks** - Keep diagram content contiguous

## stateDiagram-v2

### Known Limitations

- **Do NOT use `::` in transition labels** - The `::` sequence is interpreted as special syntax
  ```mermaid
  %% BAD - will cause parse error
  stateDiagram-v2
      [*] --> Created: Link::Created

  %% GOOD - use spaces or other separators
  stateDiagram-v2
      [*] --> Created : Link Created
      [*] --> Created : Link/Created
      [*] --> Created : Link_Created
  ```

- **State names must be simple identifiers** - No special characters in state names
- **Use spaces around `:` in transitions** - `A --> B : label` not `A --> B:label`

## flowchart / graph

### Syntax Tips

```mermaid
flowchart TD
    %% Node shapes
    A[Rectangle]
    B(Rounded)
    C([Stadium])
    D[[Subroutine]]
    E[(Database)]
    F((Circle))
    G{Diamond}
    H{{Hexagon}}

    %% Labels with special chars need quotes
    I["Label with (parens)"]
    J["Label with [brackets]"]
```

### Known Limitations

- **Escape special characters in labels** - Use quotes and HTML entities when needed
- **Subgraph IDs must be unique** - Don't reuse IDs across subgraphs

## sequenceDiagram

### Syntax Tips

```mermaid
sequenceDiagram
    participant A as Alice
    participant B as Bob

    A->>B: Solid arrow
    A-->>B: Dashed arrow
    A-xB: Cross end
    A--xB: Dashed cross

    Note over A,B: Note spanning participants

    alt Condition
        A->>B: If true
    else Other
        A->>B: If false
    end

    loop Every minute
        A->>B: Repeated
    end
```

### Known Limitations

- **Participant names with spaces** - Use `participant X as "Name With Spaces"`
- **Messages cannot contain `-->`** - This is reserved syntax

## erDiagram

### Syntax Tips

```mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE_ITEM : contains
    PRODUCT ||--o{ LINE_ITEM : "is in"
```

### Cardinality Symbols

| Symbol | Meaning |
|--------|---------|
| `\|\|` | Exactly one |
| `o\|` | Zero or one |
| `}o` | Zero or many |
| `}\|` | One or many |

### Known Limitations

- **Entity names must be single words** - Use underscores: `LINE_ITEM` not `Line Item`
- **Relationship labels with spaces need quotes** - `"is in"` not `is in`

## classDiagram

### Syntax Tips

```mermaid
classDiagram
    class Animal {
        +String name
        +int age
        +makeSound() void
    }

    Animal <|-- Dog : extends
    Dog *-- Tail : composition
    Dog o-- Owner : aggregation
```

### Known Limitations

- **Generic types** - Use `List~String~` not `List<String>` (tildes instead of angle brackets)
- **Method signatures** - Keep them simple, complex signatures may not parse

## gantt

### Syntax Tips

```mermaid
gantt
    title Project Timeline
    dateFormat YYYY-MM-DD

    section Phase 1
    Task 1 :a1, 2024-01-01, 30d
    Task 2 :after a1, 20d

    section Phase 2
    Task 3 :2024-02-01, 15d
```

### Known Limitations

- **Task names cannot contain `:` or `,`** - These are delimiter characters
- **Section names cannot be empty** - Must have at least one character

## Viewing Diagrams

Use the mermaid_view tool to render diagrams in the browser:
```bash
~/wealthsimple/scripts/mermaid_view/mermaid_view.js "flowchart TD\n    A --> B"
```

## Troubleshooting

If a diagram fails to render:

1. **Check for reserved characters** - `::`, `-->`, `|`, etc. in labels
2. **Validate quotes** - Labels with special chars need proper quoting
3. **Simplify and rebuild** - Start with minimal diagram, add complexity incrementally
4. **Check Mermaid version** - Some syntax is version-specific

---
name: generate-layer-mapping-diagram
description: Generate a three-column Mermaid diagram showing how DSL-layer operations map to DomainOperations and then to FAIR instructions for a given analysis
author: Eric Bodden
version: 0.0.2
---

You are a software architecture documentation expert for the SOSA-DSL-FAIR project. Your task is to generate a three-column Mermaid diagram that traces how each operation flows through the three abstraction layers of the project:

1. **DSL Layer** — Builder-level operations defined in `src/main/kotlin/dsl/`
2. **DomainOperation Layer** — Intermediate algebraic operations (implementations of the `DomainOperation` interface)
3. **FAIR Instruction Layer** — Low-level IR instructions (subtypes of `FAIRStmt` in `fair.core/`)

## Input

You are given the name of an analysis DSL definition as an argument (e.g., `TaintAnalysis`, `TypestateAnalysis`, `ConstantPropAnalysis`).

## Steps

1. **Locate the analysis definition.** Find the Kotlin file in `src/main/kotlin/dsl/examples/` that defines the analysis via a `fairAnalysis { ... }` builder call. If it does not exist, notify the user and exit.

2. **Discover the current DSL API.** Read the builder classes in `src/main/kotlin/dsl/` to understand what DSL-level operations currently exist and what their builder method signatures are. Do not assume any fixed set of operations — discover them from the code.

3. **Read the analysis definition.** Parse the builder calls made in the analysis definition file. Identify every DSL-level operation used, both explicit calls and implicit defaults (defaults are defined in the builder classes and apply when the analysis definition does not override them).

4. **Discover current DomainOperations.** Read the `DomainOperation` interface and all its implementations in `src/main/kotlin/dsl/` to understand the current set of operations. For each DSL call identified in step 3, trace through the builder code to determine which `DomainOperation` it produces.

5. **Discover current FAIR instructions.** Read the FAIR statement types in `fair.core/` and the conversion/semantics code to understand how `DomainOperation`s are embedded into FAIR instructions. Trace each `DomainOperation` to the FAIR instruction it ends up in.

6. **Generate the diagram.** Produce a Markdown file with:
   - A `graph LR` Mermaid diagram with three subgraph columns (DSL Layer, DomainOperation Layer, FAIR Instruction Layer)
   - Arrows connecting each DSL operation to its DomainOperation and then to its FAIR instruction
   - Include both explicit DSL calls from the definition AND implicit defaults
   - A summary table below the diagram with columns: DSL Call | Example | DomainOperation | FAIR Instruction

7. **Output location.** Write the file to `docs/<analysis-name-lowercase>-layers.md` (e.g., `docs/taint-layers.md`). If the file already exists, overwrite it with the updated version.

## Diagram Style

- Use `graph LR` (left-to-right) orientation
- Each layer is a `subgraph` with `direction TB` (top-to-bottom) for internal layout
- Node labels should be concise but descriptive (e.g., show the DSL call with its effect builder method)
- Use descriptive FAIR instruction labels showing the operator and args pattern
- Group related operations where it makes sense (e.g., multiple arithmetic ops sharing the same DomainOperation type can share a single middle-layer node)
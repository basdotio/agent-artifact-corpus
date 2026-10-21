/**
 * MarkdownExtractor Unit Tests
 */

import { describe, expect, test, beforeAll, afterAll } from "bun:test";
import { Effect } from "effect";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  MarkdownExtractor,
  MarkdownExtractorLive,
  sanitizeText,
} from "./MarkdownExtractor.js";

// ============================================================================
// sanitizeText() Tests
// ============================================================================

describe("sanitizeText", () => {
  test("strips null bytes from markdown text", () => {
    const input = "Hello\x00World\x00!";
    const result = sanitizeText(input);
    expect(result).toBe("HelloWorld!");
  });

  test("strips multiple consecutive null bytes", () => {
    const input = "Text\x00\x00\x00with\x00\x00nulls";
    const result = sanitizeText(input);
    expect(result).toBe("Textwithnulls");
  });

  test("handles text with no null bytes", () => {
    const input = "Clean markdown text";
    const result = sanitizeText(input);
    expect(result).toBe("Clean markdown text");
  });

  test("handles empty string", () => {
    const input = "";
    const result = sanitizeText(input);
    expect(result).toBe("");
  });

  test("preserves unicode in markdown", () => {
    const input = "café\x00naïve\x00résumé";
    const result = sanitizeText(input);
    expect(result).toBe("cafénaïverésumé");
  });

  test("preserves markdown syntax", () => {
    const input = "# Heading\x00\n\n**bold**\x00";
    const result = sanitizeText(input);
    expect(result).toBe("# Heading\n\n**bold**");
  });
});

// ============================================================================
// Test Helpers
// ============================================================================

let tempDir: string;

beforeAll(() => {
  tempDir = mkdtempSync(join(tmpdir(), "md-extractor-test-"));
});

afterAll(() => {
  rmSync(tempDir, { recursive: true, force: true });
});

function writeTempFile(name: string, content: string): string {
  const path = join(tempDir, name);
  writeFileSync(path, content, "utf-8");
  return path;
}

function runExtract(path: string) {
  return Effect.runPromise(
    Effect.gen(function* () {
      const extractor = yield* MarkdownExtractor;
      return yield* extractor.extract(path);
    }).pipe(Effect.provide(MarkdownExtractorLive))
  );
}

function runProcess(path: string) {
  return Effect.runPromise(
    Effect.gen(function* () {
      const extractor = yield* MarkdownExtractor;
      return yield* extractor.process(path);
    }).pipe(Effect.provide(MarkdownExtractorLive))
  );
}

function runExtractFrontmatter(path: string) {
  return Effect.runPromise(
    Effect.gen(function* () {
      const extractor = yield* MarkdownExtractor;
      return yield* extractor.extractFrontmatter(path);
    }).pipe(Effect.provide(MarkdownExtractorLive))
  );
}

// ============================================================================
// Frontmatter Parsing Tests
// ============================================================================

describe("Frontmatter Parsing", () => {
  test("extracts valid YAML frontmatter with title, description, tags", async () => {
    const path = writeTempFile(
      "full-frontmatter.md",
      `---
title: My Document
description: A test document
tags:
  - test
  - markdown
---

# Content here
`
    );

    const result = await runExtract(path);
    expect(result.frontmatter.title).toBe("My Document");
    expect(result.frontmatter.description).toBe("A test document");
    expect(result.frontmatter.tags).toEqual(["test", "markdown"]);
  });

  test("extracts frontmatter with only title", async () => {
    const path = writeTempFile(
      "title-only.md",
      `---
title: Just a Title
---

Some content.
`
    );

    const result = await runExtract(path);
    expect(result.frontmatter.title).toBe("Just a Title");
    expect(result.frontmatter.description).toBeUndefined();
    expect(result.frontmatter.tags).toBeUndefined();
  });

  test("returns empty object for missing frontmatter", async () => {
    const path = writeTempFile(
      "no-frontmatter.md",
      "# Just a heading\n\nSome content."
    );

    const result = await runExtract(path);
    expect(result.frontmatter.title).toBeUndefined();
    expect(
      Object.keys(result.frontmatter).filter(
        (k) => result.frontmatter[k] !== undefined
      )
    ).toHaveLength(0);
  });

  test("handles malformed YAML gracefully", async () => {
    const path = writeTempFile(
      "malformed.md",
      `---
title: [unclosed bracket
invalid: yaml: here
---

Content after bad frontmatter.
`
    );

    // Should not throw, returns empty or partial
    const result = await runExtract(path);
    expect(result).toBeDefined();
    expect(result.sections.length).toBeGreaterThan(0);
  });

  test("preserves extra frontmatter fields", async () => {
    const path = writeTempFile(
      "extra-fields.md",
      `---
title: Doc
author: John Doe
date: 2024-01-01
custom_field: custom_value
---

Content.
`
    );

    const result = await runExtract(path);
    expect(result.frontmatter.title).toBe("Doc");
    expect(result.frontmatter.author).toBe("John Doe");
    expect(result.frontmatter.custom_field).toBe("custom_value");
  });

  test("extractFrontmatter method works independently", async () => {
    const path = writeTempFile(
      "fm-only.md",
      `---
title: Fast Path Test
---

# Heading
Content that we don't need to parse.
`
    );

    const fm = await runExtractFrontmatter(path);
    expect(fm.title).toBe("Fast Path Test");
  });
});

// ============================================================================
// Section Extraction Tests
// ============================================================================

describe("Section Extraction", () => {
  test("extracts single H1 heading", async () => {
    const path = writeTempFile(
      "single-h1.md",
      "# Main Title\n\nSome content here."
    );

    const result = await runExtract(path);
    expect(result.sections).toHaveLength(1);
    expect(result.sections[0].heading).toBe("Main Title");
    expect(result.sections[0].headingLevel).toBe(1);
    expect(result.sections[0].text).toBe("Some content here.");
  });

  test("extracts multiple headings at different levels", async () => {
    const path = writeTempFile(
      "multi-heading.md",
      `# H1 Title

First section content.

## H2 Section

Second section content.

### H3 Subsection

Third section content.
`
    );

    const result = await runExtract(path);
    expect(result.sections).toHaveLength(3);
    expect(result.sections[0].heading).toBe("H1 Title");
    expect(result.sections[0].headingLevel).toBe(1);
    expect(result.sections[1].heading).toBe("H2 Section");
    expect(result.sections[1].headingLevel).toBe(2);
    expect(result.sections[2].heading).toBe("H3 Subsection");
    expect(result.sections[2].headingLevel).toBe(3);
  });

  test("handles document with no headings", async () => {
    const path = writeTempFile(
      "no-headings.md",
      "Just plain text content.\n\nWith multiple paragraphs.\n\nNo headings at all."
    );

    const result = await runExtract(path);
    expect(result.sections).toHaveLength(1);
    expect(result.sections[0].heading).toBe("");
    expect(result.sections[0].text).toContain("Just plain text content");
  });

  test("handles content before first heading", async () => {
    const path = writeTempFile(
      "content-before.md",
      `Some intro text before any heading.

# First Heading

Content after heading.
`
    );

    const result = await runExtract(path);
    // Content before heading becomes section 1, heading becomes section 2
    expect(result.sections.length).toBeGreaterThanOrEqual(1);
  });

  test("handles empty sections (heading with no content)", async () => {
    const path = writeTempFile(
      "empty-section.md",
      `# First

# Second

Content only in second.
`
    );

    const result = await runExtract(path);
    expect(result.sections.length).toBeGreaterThanOrEqual(1);
    // At least one section should have the content
    const hasContent = result.sections.some((s) =>
      s.text.includes("Content only")
    );
    expect(hasContent).toBe(true);
  });

  test("handles headings with special characters", async () => {
    const path = writeTempFile(
      "special-chars.md",
      `# Hello & Goodbye: A "Test" <Document>

Content here.
`
    );

    const result = await runExtract(path);
    expect(result.sections[0].heading).toBe(
      'Hello & Goodbye: A "Test" <Document>'
    );
  });

  test("handles GFM features (tables, strikethrough)", async () => {
    const path = writeTempFile(
      "gfm.md",
      `# GFM Test

| Column 1 | Column 2 |
|----------|----------|
| Cell 1   | Cell 2   |

~~strikethrough~~ and **bold**.
`
    );

    const result = await runExtract(path);
    expect(result.sections).toHaveLength(1);
    expect(result.sections[0].text).toContain("Column 1");
    expect(result.sections[0].text).toContain("strikethrough");
  });
});

// ============================================================================
// Chunking Logic Tests
// ============================================================================

describe("Chunking Logic", () => {
  test("text shorter than chunk size returns single chunk", async () => {
    const path = writeTempFile("short.md", "# Title\n\nShort content.");

    const result = await runProcess(path);
    expect(result.chunks.length).toBe(1);
  });

  test("splits on paragraph boundaries", async () => {
    const path = writeTempFile(
      "paragraphs.md",
      `# Title

${"First paragraph. ".repeat(50)}

${"Second paragraph. ".repeat(50)}

${"Third paragraph. ".repeat(50)}
`
    );

    const result = await runProcess(path);
    expect(result.chunks.length).toBeGreaterThan(1);
  });

  test("preserves code block content (not split mid-block)", async () => {
    const path = writeTempFile(
      "code-block.md",
      `# Code Example

\`\`\`javascript
function hello() {
  console.log("Hello, world!");
  return true;
}
\`\`\`

Some text after.
`
    );

    const result = await runProcess(path);
    // Code block content should be preserved (fences stripped by mdast-util-to-string)
    const codeChunk = result.chunks.find((c) =>
      c.content.includes("console.log")
    );
    expect(codeChunk).toBeDefined();
    expect(codeChunk?.content).toContain("function hello");
  });

  test("preserves inline code content", async () => {
    const path = writeTempFile(
      "inline-code.md",
      "# Inline\n\nUse `const x = 1` for variables."
    );

    const result = await runProcess(path);
    // Inline code content preserved (backticks stripped by mdast-util-to-string)
    const chunk = result.chunks.find((c) => c.content.includes("const x = 1"));
    expect(chunk).toBeDefined();
  });

  test("filters tiny chunks (<20 chars)", async () => {
    const path = writeTempFile(
      "tiny.md",
      `# Title

${"Long content here. ".repeat(100)}

x
`
    );

    const result = await runProcess(path);
    // No chunk should be less than 20 chars
    for (const chunk of result.chunks) {
      expect(chunk.content.length).toBeGreaterThanOrEqual(20);
    }
  });

  test("handles very long sentences with hard split", async () => {
    const longSentence = "word ".repeat(200) + ".";
    const path = writeTempFile(
      "long-sentence.md",
      `# Title\n\n${longSentence}`
    );

    const result = await runProcess(path);
    // Should have multiple chunks due to hard split
    expect(result.chunks.length).toBeGreaterThan(1);
  });
});

// ============================================================================
// Edge Cases
// ============================================================================

describe("Edge Cases", () => {
  test("handles empty file", async () => {
    const path = writeTempFile("empty.md", "");

    const result = await runExtract(path);
    expect(result.sections).toHaveLength(0);
    expect(result.sectionCount).toBe(0);
  });

  test("handles file with only frontmatter", async () => {
    const path = writeTempFile(
      "only-fm.md",
      `---
title: Only Frontmatter
---
`
    );

    const result = await runExtract(path);
    expect(result.frontmatter.title).toBe("Only Frontmatter");
    // May have 0 sections or 1 empty section
    expect(result.sections.length).toBeLessThanOrEqual(1);
  });

  test("handles file with only whitespace", async () => {
    const path = writeTempFile("whitespace.md", "   \n\n   \t\t\n   ");

    const result = await runExtract(path);
    expect(result.sections).toHaveLength(0);
  });

  test("handles unicode and emoji content", async () => {
    const path = writeTempFile(
      "unicode.md",
      `# Hello World

Content with emojis and unicode: café, naïve, résumé.
`
    );

    const result = await runExtract(path);
    expect(result.sections[0].text).toContain("café");
    expect(result.sections[0].text).toContain("naïve");
  });

  test("handles Windows line endings (CRLF)", async () => {
    const path = writeTempFile(
      "crlf.md",
      "# Title\r\n\r\nContent with CRLF.\r\n"
    );

    const result = await runExtract(path);
    expect(result.sections).toHaveLength(1);
    expect(result.sections[0].heading).toBe("Title");
  });

  test("returns error for non-existent file", async () => {
    const path = join(tempDir, "does-not-exist.md");

    expect(runExtract(path)).rejects.toThrow();
  });
});

// ============================================================================
// Integration Tests
// ============================================================================

describe("Integration", () => {
  test("process() returns frontmatter with chunks", async () => {
    const path = writeTempFile(
      "integration.md",
      `---
title: Integration Test
tags:
  - test
---

# Section One

Content for section one.

# Section Two

Content for section two.
`
    );

    const result = await runProcess(path);
    expect(result.frontmatter.title).toBe("Integration Test");
    expect(result.frontmatter.tags).toEqual(["test"]);
    expect(result.pageCount).toBe(2);
    expect(result.chunks.length).toBeGreaterThanOrEqual(2);
  });

  test("chunks include heading context", async () => {
    const path = writeTempFile(
      "heading-context.md",
      `# Important Section

This is the content.
`
    );

    const result = await runProcess(path);
    // Chunk should include the heading for context
    const chunk = result.chunks[0];
    expect(chunk.content).toContain("Important Section");
  });

  test("process() strips null bytes from content", async () => {
    const path = writeTempFile(
      "null-bytes.md",
      `# Title with\x00null bytes

Content with\x00\x00multiple\x00null bytes.
`
    );

    const result = await runProcess(path);
    // Verify no null bytes in any chunk
    for (const chunk of result.chunks) {
      expect(chunk.content).not.toContain("\x00");
      expect(chunk.content).toContain("null bytes");
    }
  });
});

---
name: ebook-creator
description: "Use this skill when users want to write, format, or publish e-books, digital books, or Kindle content. Triggers: e-book, ebook, kindle, epub, digital book, publish book, book cover, book formatting, self-publishing, amazon kdp, criar e-book, livro digital."
allowed-tools: [Read, Write, Edit, Bash, Browser]
license: MIT License
metadata:
    skill-author: Lucas Kefler Bergamaschi
---

# E-book Creator

## Overview
This skill empowers Manus to create complete, professional-grade e-books from various source materials. It handles everything from initial content structuring and formatting to cover design and final publication on popular e-book platforms. Use this skill when you need to transform raw text, articles, or research into a polished, distributable digital book.

## Automatic Triggers

**ALWAYS activate this skill when user mentions:**
- Keywords: e-book, ebook, kindle, epub, mobi, digital book, publish book, book cover, book formatting, self-publishing, amazon kdp, criar e-book, livro digital, formatar livro, publicar livro, capa de livro.
- Phrases: "create an e-book", "format my book", "publish on Amazon", "design a book cover", "criar um e-book", "formatar meu livro", "publicar na Amazon", "capa para meu e-book".
- Context: Any discussion about writing, formatting, designing, or publishing digital books, especially for platforms like Kindle.

## When to Use This Skill
**ALWAYS use this skill when user mentions:**
- **Content Repurposing:** Converting blog posts, articles, or research into an e-book.
- **Lead Generation:** Creating an e-book as a lead magnet.
- **Digital Product Creation:** Developing an e-book for sale (e.g., on Amazon KDP).
- **Documentation:** Compiling guides or manuals into an e-book format.
- **Personal Projects:** Turning personal stories or collections into a shareable e-book.

## Core Capabilities

### 1. Content Structuring and Formatting
- **Markdown to E-book:** Ingests Markdown files and intelligently structures them into chapters, sections, and subsections.
- **Table of Contents Generation:** Automatically creates a clickable, multi-level table of contents based on the document's heading structure.
- **Advanced Formatting:** Supports a wide range of formatting options, including blockquotes, code blocks with syntax highlighting, footnotes, and image embedding.
- **Template-Based Styling:** Applies pre-defined or custom CSS templates to ensure consistent and professional styling across the entire e-book.

### 2. Cover Design
- **AI-Powered Cover Generation:** Utilizes generative AI tools to create unique and compelling e-book covers based on a text prompt describing the book's theme, genre, and desired style.
- **Image Integration:** Allows the use of existing images or stock photos as the basis for the cover design.
- **Text Overlay:** Adds the book title, author name, and subtitle to the cover image with professional typography.

### 3. Multi-Format Export
- **EPUB Generation:** Exports the e-book into the widely-supported EPUB format, compatible with most e-readers and devices (Kindle, Kobo, Apple Books, etc.).
- **MOBI/KDP Generation:** Creates files specifically optimized for Amazon's Kindle platform.
- **PDF Export:** Generates a high-quality PDF version suitable for printing or digital distribution where a fixed layout is preferred.

### 4. Platform Publishing (Experimental)
- **Metadata Packaging:** Gathers and formats all necessary metadata, including title, author, description, keywords, and categories, for platform submission.
- **Automated KDP Submission:** (Requires user credentials) Can automate the process of uploading the e-book, cover, and metadata to the Amazon KDP platform.

## Step-by-Step Workflow

1.  **Initialize the Project:**
    - Create a new directory for your e-book project.
    - Inside the directory, create a `content` subdirectory.
    - Place your source Markdown files inside the `content` directory. It's best to separate chapters into different files (e.g., `01-introduction.md`, `02-chapter-one.md`).

2.  **Prepare the Content:**
    - Ensure your Markdown files are well-structured with proper use of headings (`#`, `##`, `###`). These will be used to build the Table of Contents.
    - Add images to an `images` subdirectory within your project and reference them in your Markdown using relative paths (e.g., `![My Image](../images/my-image.png)`).

3.  **Configure the E-book:**
    - Create a `config.yml` file in the project's root directory.
    - Define the e-book's metadata in this file.

    ```yaml
    # config.yml
    title: "My Awesome E-book"
    author: "Your Name"
    language: "en"
    cover-image: "images/cover.jpg" # Path to your cover image
    chapters:
      - "content/01-introduction.md"
      - "content/02-chapter-one.md"
      - "content/03-conclusion.md"
    ```

4.  **Generate the Cover (Optional):**
    - If you don't have a cover, you can ask Manus to generate one.
    - **User Prompt:** "Manus, create a cover for my e-book titled 'My Awesome E-book'. It's a sci-fi novel about space exploration. I want a minimalist design with a planet and a small spaceship."
    - Manus will use an image generation tool and save the result to the specified path (e.g., `images/cover.jpg`).

5.  **Build the E-book:**
    - This skill uses `pandoc`, a powerful command-line document converter, to build the e-book.
    - **User Prompt:** "Manus, build my e-book in EPUB and PDF format using the configuration in `config.yml`."
    - Manus will execute the necessary `pandoc` command.

    ```bash
    # Example pandoc command for EPUB
    pandoc --from=markdown --to=epub --output=my-ebook.epub \
           --table-of-contents --toc-depth=2 \
           --epub-cover-image=images/cover.jpg \
           --metadata-file=config.yml \
           content/01-introduction.md content/02-chapter-one.md
    ```

6.  **Review and Publish:**
    - Review the generated `my-ebook.epub` and `my-ebook.pdf` files.
    - Once satisfied, you can manually upload them to your chosen platforms or use the experimental publishing feature.

## Best Practices

- **Semantic Structure:** Use headings (`#`, `##`) semantically, not just for styling. This is crucial for an accessible and navigable Table of Contents.
- **Image Optimization:** Before including images, optimize them for the web to keep the e-book file size manageable. Use tools like `imagemagick` or online compressors.
- **Consistent Formatting:** Stick to standard Markdown. Avoid complex HTML unless absolutely necessary, as it may not render correctly in all e-book formats.
- **Proofread Thoroughly:** Read through the entire generated e-book on an actual e-reader device or app to catch any formatting errors before publishing.
- **Metadata is Key:** Spend time writing a compelling description and choosing relevant keywords and categories. This is vital for discoverability on e-book stores.

## Examples

### Example 1: Creating a Simple E-book from a Single File

- **Project Structure:**
  ```
  /my-first-ebook
  ├── content.md
  └── cover.jpg
  ```

- **`content.md`:**
  ```markdown
  % My First E-book
  % John Doe

  # Introduction
  This is the introduction to my first e-book.

  # Chapter 1
  This is the first chapter. It has some **bold** text and a list:

  - Item 1
  - Item 2
  ```

- **User Prompt:** "Manus, create an EPUB e-book from `content.md`. Use `cover.jpg` as the cover. The title is 'My First E-book' and the author is 'John Doe'."

- **Resulting Command:**
  ```bash
  pandoc content.md -o my-first-ebook.epub --epub-cover-image=cover.jpg
  ```

### Example 2: Multi-Chapter E-book with a Config File

- **Project Structure:**
  ```
  /tech-guide
  ├── config.yml
  ├── images/
  │   └── cover.png
  └── content/
      ├── 00-intro.md
      ├── 01-setup.md
      └── 02-advanced.md
  ```

- **`config.yml`:**
  ```yaml
  title: "The Ultimate Tech Guide"
  author: "Jane Smith"
  language: "en-US"
  rights: "© 2026 Jane Smith. All rights reserved."
  ```

- **User Prompt:** "Manus, build the e-book defined in `tech-guide/`. Use the `config.yml` for metadata and the files in the `content` directory as chapters. Export to EPUB and PDF."

- **Resulting Commands:**
  ```bash
  # For EPUB
  pandoc -o tech-guide.epub --from markdown --toc --toc-depth=2 \
         --metadata-file=tech-guide/config.yml \
         --epub-cover-image=tech-guide/images/cover.png \
         tech-guide/content/*.md

  # For PDF (requires LaTeX installation)
  pandoc -o tech-guide.pdf --from markdown --toc --toc-depth=2 \
         --metadata-file=tech-guide/config.yml \
         --pdf-engine=xelatex \
         tech-guide/content/*.md
  ```

## Templates

### Basic `config.yml` Template
```yaml
# E-book Metadata Configuration

# Required Fields
title: "Your E-book Title"
author: "Your Name"
language: "en" # Use ISO 639-1 language codes

# Optional but Recommended
date: "2026-02-02" # Publication date
rights: "© 2026 Your Name. All rights reserved."
publisher: "Your Publishing House or Name"
description: "A short, compelling description of your e-book."
keywords: ["keyword1", "keyword2", "ebook", "guide"]

# File Configuration
# cover-image: "path/to/your/cover.jpg"
# chapters:
#   - "content/01-introduction.md"
#   - "content/02-main-content.md"
#   - "content/03-conclusion.md"

# Advanced Styling (Optional)
# css: "style.css" # Path to a custom CSS file for styling
# epub-metadata: "metadata.xml" # Path to an advanced EPUB metadata file
```

### Chapter Markdown Template (`.md`)
```markdown
# Chapter Title

## Introduction to the Chapter

Start with a brief overview of what this chapter will cover. Set the stage for the reader.

## Main Section 1

Dive into the core content. Use subheadings (`###`) to break down complex topics into smaller, more digestible parts.

### Subsection 1.1

Elaborate on specific details here.

> Use blockquotes to highlight important notes, quotes, or warnings. This helps them stand out from the main text.

Here is an example of a list:

1.  **First Point:** Explain the first point in detail.
2.  **Second Point:** Explain the second point.
    - Sub-item A
    - Sub-item B

Include images to illustrate concepts:

![A descriptive caption for the image](../images/relevant-image.png)
*Figure 1: A descriptive caption.*

## Code Examples

For technical books, use fenced code blocks with language identifiers for syntax highlighting.

```python
def hello_world():
    """A simple Python function."""
    print("Hello, E-book World!")

hello_world()
```

## Chapter Summary

Conclude with a summary of the key takeaways from the chapter. This reinforces learning and provides a good transition to the next chapter.

---

*For footnotes, use this syntax.[^1]*

[^1]: This is the footnote text. It will appear at the end of the page or chapter.
```

## References

- **[Pandoc User's Guide](https://pandoc.org/MANUAL.html):** The official documentation for the Pandoc tool, which is the core engine for this skill.
- **[The EPUB 3 Standard](https://www.w3.org/publishing/epub3/):** Technical specifications for the EPUB format.
- **[Amazon KDP University](https://kdp.amazon.com/en_US/help/topic/G200782680):** Resources and guides for publishing on the Kindle platform.
- **[Markdown Guide](https://www.markdownguide.org/):** A comprehensive guide to the Markdown syntax used for writing content.

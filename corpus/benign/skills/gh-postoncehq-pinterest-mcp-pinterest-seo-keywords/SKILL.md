---
name: pinterest-seo-keywords
description: Build a Pinterest keyword set for a niche and map it to boards, pin titles and descriptions. Use when the user asks for Pinterest keywords, Pinterest SEO, keyword research for Pinterest, what to put in pin titles, or how to get pins found in Pinterest search.
metadata:
  author: PostOnce
  version: "0.1.0"
---

# Pinterest SEO keywords

Turn what the user sells or writes about into the phrases people type into Pinterest search, then map those phrases to boards and pins. This skill is advisory: the keywords come from the user's input and your judgment, not from Pinterest data. This server can't read Pinterest search volume, trends or analytics, so never present a volume, rank or "trending" claim as measured.

## Inputs to get first

- The niche and the audience (for example "vegetarian meal prep for busy parents").
- What the pins link to: blog posts, products, a shop, videos.
- 3–10 existing pages or products, if the user has them.
- Any keywords they already use or have seen in Pinterest's search suggestions. Ask them to type their main topic into Pinterest search and paste the suggestions; those are real phrases people use.

## How to build the set

1. **Head terms (3–5).** The broad topic: "meal prep", "vegetarian recipes".
2. **Descriptive phrases (10–20).** Head term plus a modifier people actually add: audience ("for beginners", "for kids"), constraint ("no bake", "under 30 minutes", "budget"), format ("ideas", "checklist", "printable"), season or occasion ("fall", "christmas").
3. **Long-tail phrases (10–20).** Specific enough that one pin fully answers them: "vegetarian meal prep for the week with a shopping list".
4. Drop anything the user's content can't honestly deliver.
5. Group phrases into 3–8 clusters. Each cluster becomes a board.

## Mapping

- **Board name:** the cluster's clearest descriptive phrase ("Vegetarian Meal Prep Ideas"). See the `pinterest-board-ideas` skill.
- **Pin title:** one long-tail or descriptive phrase, first.
- **Pin description:** the same phrase in the first sentence, plus 2–3 related phrases from the cluster, in sentences.
- **Pin image text:** a short version of the title, so the image and the words agree.

## What to avoid

- Hashtags as the keyword strategy. Words in the title and description do the work.
- The same exact title on every pin. Vary the phrase across pins that link to the same page.
- Keywords unrelated to the linked page. Pins that mislead get fewer clicks and saves.

## Output

Return a table with columns: cluster, board name, keyword phrases, and 2–3 example pin titles per cluster. Then list the top 5 phrases to start with and why. Tell the user these are starting points to check against Pinterest's own search suggestions. Offer to write pins for any cluster with the `pinterest-pin-description-generator` skill, and to schedule them with the `postonce` skill once images exist.

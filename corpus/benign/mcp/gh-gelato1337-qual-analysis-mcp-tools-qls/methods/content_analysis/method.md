# Qualitative content analysis

You are doing qualitative content analysis of interviews: a systematic, rule-guided reading in
which passages are coded into categories, and the categories are then used to describe and explain
what happened in each case and across cases. This version has three coding passes, each with its own
kind of category, followed by case descriptions:

| Pass | Categories come from | What you do |
|---|---|---|
| 1. Guide coding | the **coding frame** in `intent()`: the categories the interviews were designed around | code every relevant passage into them |
| 2. Emergent | the data | split the guide categories into finer subcategories that the passages themselves suggest |
| 3. Theory | the **theory frame** in `intent()` | re-read the coded passages through the theory and record where they fit, and where they do not |
| 4. Cases | the coded material | write each case's story and path over time, then answer the research question across cases |

The research question in `intent()` decides what counts as relevant. Passages that bear on it are
coded; small talk and the interviewer's own explanations are not.

## The objects

**Category** (`add_category`)
- `label`, `description`: a name and a definition saying what belongs and what does not.
- `origin`: `guide`, `emergent` or `theory`. Guide and theory categories come from the brief;
  never invent them. Emergent categories come from the data and name the broader category they refine
  (`parent`).
- Categories may start empty; passages are coded into them later.

**Coded segment** (`code_segment`)
- `label`: what the passage says, in one short English phrase, close to the informant's terms.
- quotes: the informant's exact words, each with a reason. Checked against the transcript.
- `categories`: at least one, each with a reason. A passage can belong to several categories.
- `period`: when it happened, as the informant places it (a year or a span), whenever they say.
- `direction`: for events and factors, whether it accelerated or decelerated the development, was a
  turning point, or neither.
- `in_vivo`: the informant's own word, if there is one.

## Rules of the method

- **Code the passage, not your interpretation of it.** The label says what the informant says.
  Interpretation belongs in memos and in the later passes.
- **Use the frame as given in pass 1.** If a passage fits no guide category but matters for the
  question, code it into the closest one and say why in the reason, or write a `residual` memo. Do
  not add guide categories.
- **Emergent categories are found, not imposed.** Create one only when several segments share
  something the guide category does not capture.
- **Theory is a lens, not a container.** In pass 3, record where the material fits the theory, and
  equally where it does not. Material that fits no theory category is a finding, not a gap.
- **Time matters.** Whenever the informant places something in time, record the period. The case
  descriptions are built from these.
- **Cases first, then across.** Describe each case on its own terms before comparing.

## Stages

| Stage | You write | Ends with |
|---|---|---|
| `frame` | the guide categories, exactly as the brief's coding frame defines them | checkpoint: the researcher checks the frame |
| `guide_coding` | coded segments for each interview, one interview per session; then a review | checkpoint after all interviews |
| `emergent` | emergent subcategories; segments recoded into them | checkpoint |
| `theory` | theory categories from the brief's theory frame; segments coded into them; a comparison memo | checkpoint |
| `cases` | a case description per interview; then the cross-case answer | checkpoint: done |

## Guides for single tasks

`guide(name)`: `coding-frame`, `segment`, `emergent`, `theory`, `case-description`.

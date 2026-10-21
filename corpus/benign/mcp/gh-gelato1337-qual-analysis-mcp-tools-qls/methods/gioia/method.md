# Gioia methodology

You are doing inductive qualitative analysis in the tradition of Gioia, Corley and Hamilton (2013).
Informants are knowledgeable agents: they know what they are doing and can explain it. Your job is to
give their account its due first, and only then to theorise about it.

The result is a **data structure**, built bottom-up in three levels, and from it a grounded model
that answers the research question in `intent()`:

| Level | Whose terms | What it is |
|---|---|---|
| **1st-order concepts** | the informants' | what informants say, close to their words and distinctions |
| **2nd-order themes** | the researcher's | what is going on here, theoretically: a phenomenon several concepts point to |
| **Aggregate dimensions** | the researcher's, in the study's lens | what the themes add up to, as an answer to the research question |

The research question and the researcher's angle shape what is worth noticing. Keep them in view:
two studies asking different questions of the same interviews should end up with different
structures. Do not produce a generic summary of what the interviews talk about.

## Why the levels are kept apart

Meaning is lost when concepts are abstracted too early. A concept that says "automation" has thrown
away who automates what, why, against what resistance, and what the informant thinks of it; nothing
built on it later can get that back. So:

- At the 1st order, stay at the informant's level even when it feels too detailed. Abstraction is the
  next stage's job, and it can only abstract what you kept.
- Prior research and theory (in `intent()`) are for later stages. While coding concepts, set them
  aside: code what the informant says, not what the literature predicts. If you notice yourself
  reaching for a theory's term, write a `reflexive` memo instead.
- At the 2nd order and above, theory is welcome, but every theme and dimension must still be
  traceable to quotes through the concepts under it.

## Stages

The run moves through these stages; the researcher reviews the work at the end of each and moves the
run on. Your task tells you which stage you are in and what to do; `status()` confirms it.

| Stage | You write | Ends with |
|---|---|---|
| `calibrate` | 1st-order concepts for a few interviews, interview memos, codebook proposals | checkpoint: researcher reviews, codebook v1 is agreed and frozen with the concept fields |
| `first_order` | 1st-order concepts for the rest, one interview at a time; batch memos | checkpoint: discussion of the concepts |
| `themes` | 2nd-order themes from concepts; may revise concepts with a reason | checkpoint: discussion of the themes |
| `dimensions` | aggregate dimensions from themes, each answering the question; negative cases | checkpoint: discussion of the dimensions |
| `revise` | revisions across levels; corpus memo with the grounded model | checkpoint: done |

## Objects and what each must carry

The database refuses objects that are missing what is marked required.

**1st-order concept**
- `label`: short, in English, close to the informant's terms. It should say something: "night nurses
  override the triage score", not "triage issues".
- `description`: one or two sentences: what informants say or do, with the conditions and direction
  they give (who, about what, for or against, under which circumstances).
- `in_vivo`: the informant's own word or phrase in the original language, when there is one.
- quotes: at least one, each with a reason saying why it shows this concept.
- Additional fields agreed for this study in calibration, if any.

**2nd-order theme**
- `label`, `description`: a researcher-centric name and definition of the phenomenon.
- concepts: at least two, each with a reason. A concept belongs to one theme only.

**Aggregate dimension**
- `label`, `description`.
- themes: at least one, each with a reason. A theme belongs to one dimension only.
- `answers`: how this dimension answers the research question.
- a `negative-case` memo: where you looked for contradicting evidence, and what you found.

## Guides for single tasks

Read the relevant one with `guide(name)` when you start that kind of work:

- `concept`: writing a 1st-order concept
- `interview-memo`: the memo you write for each interview
- `codebook`: proposing and using codebook entries
- `themes`: building 2nd-order themes
- `dimensions`: building aggregate dimensions and searching for negative cases

## Quality, in one list

- Every concept is grounded in what informants said, not in what you expect them to have meant.
- Labels say something. Test: could you have written this label without reading the interviews?
  Then it is too generic.
- Themes are more than topics: they name a phenomenon that bears on the research question.
- Dimensions answer the question; they do not merely sort the themes.
- Concepts that fit nowhere are data too: memo them rather than forcing them in.
- Write `uncertainty` memos freely; the researcher reads them first.

# Ways of working with the qls server

These hold for any method. How to do the method is in `method_guide()`; short how-tos for single
tasks are in `guide(name)` (the method guide lists them). What the study asks is in `intent()`.

## Where things are

| You need | Look in |
|---|---|
| what the study asks, from which angle, what the researchers already know | `intent()` |
| how to think in this method | `method_guide()` |
| how to do one task well (a concept, a memo, a theme ...) | `guide(name)` |
| what you have been asked to do now | the task you were given, and `status()` for the current stage |
| what we already know about the data | the codebook (`codebook()`) and memos (`memos()`) |
| the data itself | `begin(source)`, `read_source()`, `search()` |
| what the researcher said | `feedback()` |

Read the guides when a task starts, not from memory of an earlier session: they may have changed.

## Stages

The run is in one stage at a time (`status()`). The stage decides what you may write. The researcher
moves the run to the next stage; you cannot. If the task needs something the stage does not allow, do
not work around it: say so in a memo or a checkpoint question.

## Quotes

- Quote the informant's exact words, copied from the interview, at the moment you add the concept.
  Quotes are checked immediately; if a quote is not in the transcript, nothing is saved and you are
  told so. Re-read the passage (`read_source`) and copy it again. Do not paraphrase, tidy, translate,
  or join sentences from different places.
- Copy transcription marks as they are: pauses, `(-)`, `[pp]`, dialect spellings. They are part of
  the text the quote is checked against.
- Quote the shortest span that carries the meaning: usually one to three sentences.
- Only informants are quotable. Interviewer questions are context, not evidence. When an informant
  only agrees with something the interviewer said ("Juu", "Yes, exactly"), the claim is the
  interviewer's: note it, do not code it as the informant's view.

## Reasons

- Every link that needs a reason gets one line saying why it holds: "describes bypassing the official
  release process", not "relevant". Reasons are what a reviewer reads to judge your analysis, and what
  you will read later when you no longer have the interview in front of you.
- Every change (revise, merge, withdraw, remove) needs a reason. Nothing is deleted from history.

## Memory

Your context window is working memory: one interview at a time, gone when the session ends. Anything
you will need later must be written down now. Do not rely on remembering earlier interviews or
sessions; look them up (`search`, `get`, `pack`, `memos`, `query`).

| Kind of knowledge | Where it goes |
|---|---|
| a claim from the data | a method object (concept, theme ...) with quotes and reasons |
| an agreed rule for using a code | the codebook (`propose_codebook`; the researcher approves) |
| everything soft: who the informant is, tone, what surprised you, what does not fit, doubts | memos |

**Memos.** A memo is always about something (a source, a concept, a theme, another memo) and is
short. Write them while the thought is fresh, not at the end.

- Kinds: `meaning` (what a code means here, and what it does not), `informant` (the person: role,
  stance, arc), `surprise`, `uncertainty` (where you are unsure: the researcher reads these first),
  `residual` (what in this interview does not fit the codebook), `method` (a decision about how to
  apply the method), `negative-case`, `summary`, `reflexive` (how your own assumptions may be
  shaping the reading).
- Levels: `note` (about one object), `interview` (about one source), `batch` (cites interview memos),
  `corpus` (cites batch memos). A higher memo cannot float free of what it summarises. The length
  budget per level is enforced.
- How to write the interview memo: `guide("interview-memo")`.

**Codebook.** The codebook is the shared long-term memory: the rules everyone codes by. Use approved
entries consistently. When an entry nearly fits, the difference is information: memo it and propose
a change rather than bending the entry or the data.

## Residuals: what does not fit

The risk is not forgetting; it is forcing new material into existing codes. For every interview, ask
what here does not fit the codebook, and write it down (`residual` memo) even when the answer is
"nothing, because ...". A residual that recurs across interviews is a candidate code.

## Team

Other scholars may be working on the same run. You share the codebook and the graph, not each other's
context. Say what you mean in labels, descriptions, codebook proposals and memos.

## Outside sources

You do not need the web or other documents for this work. Do not look up publications about the data
you are analysing: the analysis must come from the interviews and the brief in `intent()`. If you
recognise the data or think you know what others found in it, say so in a `reflexive` memo and keep
it out of the analysis.

## Stopping

- When your task or the method calls for it, or when you are unsure about something that matters,
  call `checkpoint(summary, questions)` and stop. Writes are blocked until the researcher resumes.
- Ask real questions: ones whose answer changes what you do next. Put your own best answer next to
  each question.
- When you resume, read `feedback()` first and act on it before anything else.

---
name: teach
description: Teach the user a new skill or concept, within this workspace. Produces beautiful, self-contained, interactive HTML lessons.
disable-model-invocation: true
argument-hint: "What would you like to learn about?"
---

The user has asked you to teach them something. This is a stateful request - they intend to learn the topic over multiple sessions.

## Teaching Workspace

Treat the current directory as a teaching workspace. The state of their learning is captured in this directory in several files:

- `MISSION.md`: A document capturing the _reason_ the user is interested in the topic. This should be used to ground all teaching. Use the format in [MISSION-FORMAT.md](./MISSION-FORMAT.md).
- `./reference/*.html`: A directory of reference materials. These are the compressed learnings from the lessons - cheat sheets, reference algorithms, syntax, yoga poses, glossaries. They are the raw units of learning. They should be beautiful documents which print out well, and are designed for quick reference.
- `RESOURCES.md`: A list of resources which can be explored to ground your teaching in contextual knowledge, or to acquire knowledge and wisdom. Use the format in [RESOURCES-FORMAT.md](./RESOURCES-FORMAT.md).
- `./learning-records/*.md`: A directory of learning records, which capture what the user has learned. These are loosely equivalent to architectural decision records in software development - they capture non-obvious lessons and key insights that may need to be revised later, or drive future sessions. These should be used to calculate the zone of proximal development. They are titled `0001-<dash-case-name>.md`, where the number increments each time. Use the format in [LEARNING-RECORD-FORMAT.md](./LEARNING-RECORD-FORMAT.md).
- `./lessons/*.html`: A directory of lessons. A **lesson** is a single, self-contained HTML output that teaches one tightly-scoped thing tied to the mission. This is the primary unit of teaching in this workspace.
- `./assets/*`: Reusable **components** shared across lessons. See [Assets](#assets).
- `NOTES.md`: A scratchpad for you to jot down user preferences, or working notes.

## Philosophy

To learn at a deep level, the user needs three things:

- **Knowledge**, captured from high-quality, high-trust resources
- **Skills**, acquired through highly-relevant interactive lessons devised by you, based on the knowledge
- **Wisdom**, which comes from interacting with other learners and practitioners

Before the `RESOURCES.md` is well-populated, your focus should be to find high-quality resources which will help the user acquire knowledge. Never trust your parametric knowledge.

Some topics may require more skills than knowledge. Learning more about theoretical physics might be more knowledge-based. For yoga, more skills-based.

### Fluency vs Storage Strength

You should be careful to split between two types of learning:

- **Fluency strength**: in-the-moment retrieval of knowledge
- **Storage strength**: long-term retention of knowledge

Fluency can give the user an illusory sense of mastery, but storage strength is the real goal. Try to design lessons which build long-term retention by desirable difficulty:

- Using retrieval practice (recall from memory)
- Spacing (distributing practice over time)
- Interleaving (mixing up different but related topics in practice - for skills practice only)

## Lessons

A lesson is the main thing you produce — the unit in which knowledge and skills reach the user. Each lesson is one self-contained HTML file, saved to `./lessons/` and titled `0001-<dash-case-name>.html` where the number increments each time.

A lesson should be **beautiful** — clean, readable typography and layout — since the user will return to these later to review. Think Tufte. The visual + interactive system that makes this real — design tokens, layout primitives, the recall widgets, and the offline/print rules — is already built. **Don't invent it per lesson: inline the shared kit and imitate the golden example.** See [The lesson design system](#the-lesson-design-system).

The lesson should be short, and completable very quickly. Learners' working memory is very small, and we need to stay within it. But each lesson should give the user a single tangible win that they can build on. It should be directly tied to the mission, and should be in the user's zone of proximal development.

If possible, open the lesson file for the user by running a CLI command.

Each lesson should link via HTML anchors to other lessons and reference documents.

Each lesson should recommend a primary source for the user to read or watch. This should be the most high-quality, high-trust resource you found on the topic.

Each lesson should contain a reminder to ask followup questions to the agent. The agent is their teacher, and can assist with anything that's unclear.

## The lesson design system

Every lesson is one self-contained, offline, printable HTML file built from a shared visual kit — so lessons look like one coherent course and a good result is guaranteed, not left to chance. **Before writing a lesson, read the contract and open the golden example — it carries the taste. Then match it.**

- **[references/HTML-LESSON.md](./references/HTML-LESSON.md)** — the artifact contract: the required skeleton, how to inline the kit, the print/degradation rules, the design tokens, and the anti-slop checklist. Start here.
- **[references/VISUAL-TREATMENT-MAP.md](./references/VISUAL-TREATMENT-MAP.md)** — which visual primitive fits which content. Never default to a bullet list.
- **[references/INTERACTION-MENU.md](./references/INTERACTION-MENU.md)** — the retrieval-first recall widgets and their exact markup. **Every lesson needs at least one.**
- **[assets/lesson-kit.css](./assets/lesson-kit.css)** + **[assets/lesson-kit.js](./assets/lesson-kit.js)** — the shared source of truth, **inlined** into each lesson (never linked) so the file stays self-contained and offline.
- **[examples/0001-golden-example.html](./examples/0001-golden-example.html)** — a complete reference lesson. Imitate its structure and restraint.

After writing a lesson, **validate it**: `node scripts/validate-lesson.mjs ./lessons/NNNN-*.html`. It checks the required landmarks, the offline rule, the recall surface, and the citation. A lesson that doesn't pass is not finished. Then open it and eyeball it in light, dark, and print preview.

To start from a correct shell, run `node scripts/scaffold-lesson.mjs "Lesson title"`, fill the body,
then run `node scripts/inline-kit.mjs ./lessons/NNNN-slug.html` before validating.

_Optional modules_ — only when the subject genuinely calls for it (e.g. language learning or
flashcard-shaped definitions): `assets/learner-model.js`, `assets/fsrs-scheduler.js`, and
`assets/tts-readaloud.js`. Inline an optional module as a separate script after the core kit for that
lesson only; never add it to the default skeleton or golden examples. For remembering progress across
sessions, prefer writing a markdown [learning record](./LEARNING-RECORD-FORMAT.md) over any
client-side model unless the user explicitly wants local adaptive behavior.

## Assets

Lessons are built from reusable **components**, stored in `./assets/`: stylesheets, quiz widgets, simulators, diagram helpers — anything a second lesson could reuse.

Reuse is the default, not the exception. The shared visual kit (`assets/lesson-kit.css` + `assets/lesson-kit.js`) is the first component every workspace inherits — it is the "shared stylesheet every workspace earns," and every lesson **inlines a copy** of it so the lessons look like one consistent course rather than a pile of one-offs, while each file stays self-contained and offline. When a lesson needs something new and genuinely reusable, add it to the kit (or a sibling asset) and inline it from there — never hand-roll per-lesson what a future lesson would duplicate. As the workspace grows, so should the component library.

## The Mission

Every lesson should be tied into the mission - the reason that the user is interested in learning about the topic.

If the user is unclear about the mission, or the `MISSION.md` is not populated, your first job should be to question the user on why they want to learn this.

Failing to understand the mission will mean knowledge acquisition is not grounded in real-world goals. Lessons will feel too abstract. You will have no way of judging what the user should do next.

Missions may change as the user develops more skills and knowledge. This is normal - make sure to update the `MISSION.md` and add a learning record to capture the change. Confirm with the user before changing the mission.

## Zone Of Proximal Development

Each lesson, the user should always feel as if they are being challenged 'just enough'.

The user may specify an exact thing they want to learn. If they don't, figure out their zone of proximal development by:

- Reading their `learning-records`
- Figuring out the right thing to teach them based on their mission
- Teach the most relevant thing that fits in their zone of proximal development

## Knowledge

Lessons should be designed around a skill the user is going to learn. The knowledge in the lesson should be only what's required to acquire that skill. You teach the knowledge first, then get the user to practice the skills via an interactive feedback loop.

Knowledge should first be gathered from trusted resources. Use `RESOURCES.md` to keep track of them. Lessons should be littered with citations - links to external resources to back up any claim made. This increases the trustworthiness of the lesson.

For acquiring knowledge, difficulty is the enemy. It eats working memory you need for understanding.

## Skills

If knowledge is all about acquisition, skills are about durability and flexibility. Make the knowledge stick.

For skill acquisition, difficulty is the tool. Effortful retrieval is what builds storage strength. Skills should be taught through interactive lessons. There are several tools at your disposal:

- Interactive lessons, using quizzes and light in-browser tasks
- Lessons which guide the user through a list of real-world steps to take (for instance, yoga poses)

Each of these should be based on a **feedback loop**, where the user receives feedback on their performance. This feedback loop should be as tight as possible, giving feedback immediately - and ideally automatically. The recall widgets in the [interaction menu](./references/INTERACTION-MENU.md) give this for free — prefer them over hand-rolled interactions.

For quizzes, each answer should be exactly the same number of words (and characters, if possible). Don't give the user any clues about the answer through formatting.

## Acquiring Wisdom

Wisdom comes from true real-world interaction - testing your skills outside the learning environment.

When the user asks a question that appears to require wisdom, your default posture should be to attempt to answer - but to ultimately delegate to a **community**.

A community is a place (online or offline) where the user can test their skills in the real world. This might be a forum, a subreddit, a real-world class (budget permitting) or a local interest group.

You should attempt to find high-reputation communities the user can join. If the user expresses a preference that they don't want to join a community, respect it.

## Reference Documents

While creating lessons, you should also create reference documents. Lessons can reference these documents - they are useful for tracking raw units of knowledge useful across lessons.

Lessons will rarely be revisited later - reference documents will be. They should be the compressed essence of the lesson, in a format designed for quick reference. Reference documents use the same visual kit as lessons (inline it), and should be built to **print well** — they are the layer the user keeps.
Use [references/REFERENCE-DOC.md](./references/REFERENCE-DOC.md) for the printable reference shape.

Some learning topics lend themselves to reference:

- Syntax and code snippets for programming
- Algorithms and flowcharts for processes
- Yoga poses and sequences for yoga
- Exercises and routines for fitness
- Glossaries for any topic with its own nomenclature

Glossaries, in particular, are an essential reference. Once one is created, it should be adhered to in every lesson. Use the format in [GLOSSARY-FORMAT.md](./GLOSSARY-FORMAT.md).

## `NOTES.md`

The user will sometimes express preferences of how they want to be taught, or things you should keep in mind. This is the place to record those preferences, so you can refer back to them when designing lessons or working with the user.

# teach-it

Learn a topic in theory: a guide in parts, with interactive figures, diagrams,
charts, real-world case studies and quizzes. No coding projects.

You choose how to work: **step by step** (Claude builds one part, you read it,
try the lab and ask questions, then move on) or **all at once** (Claude builds
everything, then walks you through it). The lab is a local HTML
file you open in your browser.

Files go in a `<topic>/` folder where you call the skill, in `~/learning/<topic>/`,
or both (Claude asks). A `PROGRESS.md` lets you stop and resume. The folder format
is shared with [`teach-it-with-projects`](../teach-it-with-projects/), so you can
start with theory and add projects to the same topic later.

## Usage

Manual-only (Claude won't trigger it on its own):

```
/teach-it <topic>     # start a new topic
/teach-it             # inside a topic folder: resume from PROGRESS.md
```

## Install

```bash
npx skills add jleitaom/claude-skills -g --skill teach-it
```

To install all skills as a plugin, see
[Installation](../../../README.md#installation).

# Gavel

Part of [Claude Skills by gmurad](../../README.md).

**Put a decision on trial and get a ruling you can act on.**

Gavel is a [Claude Code](https://claude.com/claude-code) skill that turns a hard question ("should we rebuild
the app?", "should I take this deal?", "should the store offer free shipping?") into a structured trial. A
defense argues for it. A prosecution argues against it and has to name a better plan. A jury of 3 to 8
specialists, each with a different lens, votes alone without seeing the others. Then a judge, who wrote down
his own view before hearing a word, weighs the evidence and rules.

You get one of five verdicts (Adopt, Adopt with conditions, Redesign, Reject, Insufficient evidence), the
reasons, the strongest dissent, and the one fact that would flip the ruling.

```
you: use gavel for this: should we move the store to a subscription model?
```

## Why a trial

Ask one chatbot whether your idea is good and it tends to agree with you. Ask a panel of them to discuss it and
they tend to agree with each other: research on debates between language models finds they drop correct
answers just to reach consensus. Neither gives you what a hard decision needs, which is the strongest case on both sides, judged
by someone who is not trying to please anyone.

A courtroom is an old answer to that problem. Gavel keeps the parts of it that are backed by research and
drops the theater. Every rule below exists because a study found that groups, juries or panels of models go wrong
without it (see [Why each rule exists](#the-rules-that-keep-it-honest)).

## What happens when you run it

```
 Setup         you pick the question, how hard the prosecution pushes, the jury, and each role's model
   │
 Filing        the clerk writes the case file: facts with sources, constraints, stakes
   │
 Pretrial      the judge sharpens the question, lists competing explanations, sets the criteria and
   │           the standard of proof, seats the jury, and seals his own first opinion
   │
 Openings      defense and prosecution write their cases at the same time, blind to each other
   │
 Rebuttals     each answers the other's strongest points (skipped in a quick trial)
   │
 Record        a script assembles the record, checks word limits, and puts the sides in random order
   │
 Jury          every juror reads the record and votes alone, in parallel, never seeing another ballot
   │
 Tally         a script checks every ballot and computes the vote, the spread and the minority report
   │
 Ruling        the judge returns fresh, opens his sealed opinion, weighs the evidence, and rules
```

Each role is a separate Claude subagent with a clean memory, so nobody can be swayed by what they were not
supposed to see. The main conversation acts as the **clerk**: it runs the setup, passes files between roles,
and reports the ruling, but it never argues, votes or edits anything a role wrote.

## The setup

When you say "use Gavel for this", the skill asks a few questions with tap to choose menus.

| Question | Choices | Default |
|---|---|---|
| The question | You type it in one sentence | |
| How hard should the prosecution push? | Fair · Tough · Ruthless | Tough |
| Who sits on the jury? | The judge picks · I'll choose the seats · Quick trial (3 seats, no rebuttals) | Judge picks 5 |
| Model for the judge | Opus · Fable · Sonnet · Same as this chat | Opus |
| Model for the defense | Sonnet · Opus · Fable · Haiku | Sonnet |
| Model for the prosecution | Sonnet · Opus · Fable · Haiku | Sonnet |
| Default model for the jury | Sonnet · Haiku · Opus · Fable | Sonnet |

If you choose the seats, you pick from the bench below or type anyone you like, such as "a retired airline
pilot" or "my most demanding customer". Any seat can get its own model by adding it after a colon, like
`designer: opus`. The premortem seat always sits.

Gavel remembers your last setup. Next time, say "use my last settings" and it skips the menus.

## The courtroom, role by role

### The judge
There is one judge, and he sits twice: once before the trial and once to rule. Only the second sitting decides,
so two judges can never disagree. Each sitting is a fresh subagent on the model you chose (Opus by default,
because the ruling is the product); research found a judge brought in fresh at the end resists the biases that
build up over a long debate better than one who sat through every round.

**Pretrial.** Before any argument, the judge reads only the case file and:
1. Sharpens your question into one testable motion ("Resolved: the store should move to a subscription model").
2. Writes 3 to 5 competing explanations of what is true, including the motion, a rival plan or doing nothing,
   and one nobody has raised yet.
3. Sets 2 to 4 weighted criteria the decision should turn on (cost, risk, customer value, and so on).
4. Seats the jury: your chosen seats, or the specialists this case needs, each with its own question.
5. Sets the standard of proof (below).
6. Writes a **sealed prior**: his honest opinion and a probability, before hearing anyone. Nobody else reads it.

**Ruling.** The judge comes back with a fresh memory, opens his own sealed prior, reads the record and the
jury's ballots, and rules. He must show how far the trial moved him from his first opinion. He may overrule the
jury, but only by explaining why in writing, and the jury's vote is printed under his ruling either way.

### The defense
Argues for the motion in at most 500 words, then a 250 word rebuttal. Every claim is numbered (F1, F2) and
tagged with its support: `[case]` with a quote from the case file, `[source]` with a named source, or
`[assumption]` said plainly. Jurors give unsupported claims no weight.

### The prosecution
Argues against the motion under the same limits and tagging (claims A1, A2). The prosecution is not allowed to
just pick holes. It has to name the rival it would choose instead (another plan, or doing nothing) and lay out
the most likely way the motion fails, step by step. You choose how hard it pushes:

| Level | What it does |
|---|---|
| Fair | Builds the strongest honest case against and concedes openly what the defense will get right |
| Tough | Presses hard on the real weak points and concedes nothing the record does not prove |
| Ruthless | Assumes the motion fails and shows exactly how, attacking every claim it rests on |

At every level an attack without support counts for nothing with the jury. Ruthless means rigor, not rudeness.

### The jury
3 to 8 jurors, each a separate subagent. Every juror reads the record and nothing else, then works in a fixed
order: **facts first, vote last.**
1. Up to six findings, each tied to a claim id, graded `verified`, `plausible` or `assumption`, and marked for
   or against the motion.
2. A score from 1 to 5 on each of the judge's criteria.
3. Only then a vote: the verdict, a probability from 0 to 100 that adopting the motion is right, and a
   confidence level.
4. The decisive point, what would change their mind, and any conditions.

Jurors may also object that the question itself is badly framed.

**The bench** (the judge picks from these, or invents a seat; you can type anyone):

| Seat | The question it owns |
|---|---|
| premortem (always) | It is a year from now and this failed. What were the three most likely reasons? |
| engineer | Can this be built and run as described? What breaks first? |
| designer | Will the people it is for understand it and use it without help? |
| finance | What does it cost in total, what does it return, and when does it pay back? |
| customer | Would I pay for it or change what I do for it? |
| operations | Who runs this every day, and what does it add to their load? |
| security and privacy | What could leak, be abused, or put someone at risk? |
| legal and compliance | Which rule, contract or policy does this touch? |
| data | Does the evidence in the record actually show what it claims? |
| competitor | If I were the strongest rival, how would I answer this, and how fast? |
| domain expert | What does someone who has done this for ten years know that the record misses? |
| ethicist | Who is affected who is not in the room, and is that fair to them? |
| skeptical investor | Why now, and what has to go right that nobody has proven? |
| first time user | Coming in cold, where do I get stuck? |
| maintainer | In two years, who keeps this alive, and what does it cost to change? |

### Deliberation (optional)
With `--deliberate`, jurors get one look at the other ballots, shown as Juror A, B, C in random order, and may
revise once. Anyone who changes their verdict, or moves more than 15 points, must name the new point that moved
them. If most changes name nothing new, or everyone simply drifts toward the majority, the script throws the
second round out and the judge gets the blind vote instead.

## The verdict

| Verdict | Means |
|---|---|
| Adopt | Do it as stated |
| Adopt with conditions | Do it, provided the listed conditions are met |
| Redesign | The goal is right, the plan is not; rework it |
| Reject | Do not do it; the rival plan or doing nothing is better |
| Insufficient evidence | The record cannot support a decision yet; here is what to find out |

**Standard of proof.** The burden is always on the defense: the idea has to earn its adoption. The judge sets
the bar by how hard the decision is to undo. Cheap to reverse: *more likely than not*. Costly or hard to undo:
*clear and convincing*.

The ruling file always has the same sections: the verdict line, the ruling in plain words, how far the judge
moved from his sealed prior, the decisive evidence, the strongest dissent stated fairly, conditions, the one
fact that would flip the ruling, two or three things to watch, and the vote.

## The rules that keep it honest

| Rule | What it prevents | Research |
|---|---|---|
| Jurors vote alone before seeing anyone | Agents abandon correct answers to agree; social influence narrows opinions without making them more accurate | Wynn et al. 2025, [arXiv 2509.05396](https://arxiv.org/abs/2509.05396); Lorenz et al. 2011, [PNAS](https://pmc.ncbi.nlm.nih.gov/articles/PMC3107299) |
| Second round is optional, anonymized, and dropped if moves name no new point | Sycophancy toward peers is far more common than self bias | Choi et al. 2025, [arXiv 2510.07517](https://arxiv.org/abs/2510.07517); [arXiv 2604.02668](https://arxiv.org/abs/2604.02668) |
| At most two rounds of argument | Judge biases rise sharply after the first round | Ma et al. 2025, [arXiv 2505.19477](https://arxiv.org/abs/2505.19477) |
| Equal word limits, sides in random order | Judges favor longer answers and the first or last speaker | Khan et al. 2024, [arXiv 2402.06782](https://arxiv.org/abs/2402.06782) |
| Always two sides | Debate beat a lone advocate on every task tested, and lifted weak judges from 48% to 76% accuracy | Kenton et al. 2024, [arXiv 2407.04622](https://arxiv.org/abs/2407.04622); Khan et al. 2024 |
| The prosecution must argue a real rival | Assigned devil's advocacy is weaker than real dissent | Nemeth, Brown, Rogers 2001; Schweiger, Sandberg, Ragan 1986 |
| Judge seals his own view and lists competing explanations first | Anchoring on the first strong speaker | Heuer, *Psychology of Intelligence Analysis* (Analysis of Competing Hypotheses); Kahneman, Sibony, Lovallo (Mediating Assessments Protocol) |
| A premortem seat on every jury | Doubters stay quiet when a plan has momentum | Klein 2007, *Performing a Project Premortem*, HBR |
| Facts before votes, every finding graded | Juries that vote first cover less of the evidence | Hastie, Penrod, Pennington 1983, *Inside the Jury* |
| Evidence over headcount; the minority is always reported | Jurors on one model share blind spots; in about one in four split cases the minority was right | He et al. 2026, [arXiv 2606.29270](https://arxiv.org/abs/2606.29270) |
| Probability and confidence per juror | A bare yes or no loses how sure each juror is | Mellers et al. 2014; Satopää et al. 2014 |
| Checkable questions are sent elsewhere | On questions with a right answer, a simple vote explains most of the gain from debate | Choi et al. 2025, *Debate or Vote*, [arXiv 2508.17536](https://arxiv.org/abs/2508.17536) |

## The script that keeps it fair

The steps that should never depend on judgment are done by `scripts/gavel.py`, plain Python with no
dependencies:

| Command | What it does |
|---|---|
| `gavel.py new "<question>" [flags]` | Checks the setup, opens the case folder, saves your settings, prints the plan |
| `gavel.py settings` | Shows your last setup |
| `gavel.py pretrial CASE` | Checks the judge's pretrial plan, including that he seated exactly the jury you chose |
| `gavel.py record CASE` | Refuses speeches over the word limit, randomizes which side appears first, never includes the sealed prior |
| `gavel.py tally CASE` | Checks every ballot, computes the median and spread, flags a strong minority, audits second round changes, and shuffles the ballots under letters for the judge |
| `gavel.py close CASE` | Refuses a ruling that is missing its verdict line or any section, then adds it to the docket |
| `gavel.py list` | Every past case and its verdict |

`scripts/test_gavel.py` holds 27 tests, including deliberately broken ballots, speeches over the limit, a
herding second round, and a leaked sealed prior. Run them with `python3 scripts/test_gavel.py`.

Every case lives in its own folder under `.gavel/` in your project:

```
.gavel/2026-10-09-should-we-move-the-store-to-a-subscription/
  setup.json          your choices
  case.md             the facts
  pretrial.json       the judge's motion, explanations, criteria and jury
  sealed-prior.md     the judge's first opinion (only the judge reads it)
  opening-for.md      opening-against.md
  rebuttal-for.md     rebuttal-against.md
  record.md           what the jury reads
  ballots/round1/     one file per juror
  tally.json          the vote
  jury-packet.md      the ballots as the judge sees them
  ruling.md           the ruling
```

Case files can hold private details, so add `.gavel/` to your `.gitignore`.

## Options

| Option | Effect |
|---|---|
| `--last` | Reuse your last setup |
| `--quick` | 3 jurors and no rebuttals |
| `--deliberate` | One anonymized second round for the jury, with the herding check |
| `--research` | Both sides may search the web; every web claim needs its link |

## Cost

A trial is a lot of agent runs, so it is meant for real decisions, not quick questions.

| Trial | Runs |
|---|---|
| Quick | 2 judge + 2 speeches + 3 jurors = 7 |
| Standard | 2 judge + 4 speeches + 5 jurors = 11 |
| Standard with deliberation | 16 |

Cheaper models for the jury (Haiku) cut most of the cost. The judge is the one seat worth paying for.

## Limits, honestly

- Every juror is a Claude model, so they share blind spots. Mixing models helps a little; it does not make
  them independent. The ruling says how varied the jury was.
- No study has tested a full courtroom like this one. Each rule is grounded in research; the whole is a design.
- Nothing makes a judge immune to a persuasive argument. Word limits, random order, a sealed prior and graded
  evidence reduce the known biases; they do not remove them.
- For a question with a right answer (a bug, a fact, a calculation), a trial is the wrong tool. Gavel says so.

## Install

```sh
git clone https://github.com/gbmurad/claude-skills.git
cd claude-skills
sh install.sh gavel
```
Restart Claude Code, then say "use Gavel for this" followed by your question. Needs Python 3.

## Files

| File | What it is |
|---|---|
| `SKILL.md` | The clerk's procedure Claude follows |
| `references/roles.md` | The exact brief each role receives |
| `references/bench.md` | The juror seats and their questions |
| `references/research.md` | The evidence behind each rule |
| `scripts/gavel.py` | Case folders, word limits, ballot checks, the tally, the docket |
| `scripts/test_gavel.py` | The tests |

## License
MIT, by George Murad (see the LICENSE at the top of the repo).

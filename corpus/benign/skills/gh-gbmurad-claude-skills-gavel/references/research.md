# Gavel: why each rule exists

Every rule in the procedure answers a known way that debates, panels and juries go wrong. The sources were read
at the abstract or page level in October 2026 and checked a second time against the source; 12 of 13 matched
and one (Nemeth 2001) matched only in part because the full text was blocked.

| Rule in Gavel | The failure it prevents | Evidence |
|---|---|---|
| Jurors vote alone, in separate subagents, before seeing anyone | Agents abandon correct answers to agree with peers; social influence narrows opinion without making it more accurate | Wynn, Satija, Hadfield 2025, *Talk Isn't Always Cheap* ([arXiv 2509.05396](https://arxiv.org/abs/2509.05396)); Lorenz et al. 2011, PNAS ([PMC3107299](https://pmc.ncbi.nlm.nih.gov/articles/PMC3107299)) |
| Round 2 is optional, anonymized, and thrown out if moves name no new point | Sycophancy toward peers is far more common than self bias; it drives debates to collapse into agreement | Choi, Zhu, Li 2025, *When Identity Skews Debate* ([arXiv 2510.07517](https://arxiv.org/abs/2510.07517)); *Too Polite to Disagree* 2026 ([arXiv 2604.02668](https://arxiv.org/abs/2604.02668)); the flip rule follows the tech leads club *The Jury* skill |
| Never more than two rounds of argument | Judge biases (position, verbosity, bandwagon) rise sharply after the first round and stay up | Ma et al. 2025 ([arXiv 2505.19477](https://arxiv.org/abs/2505.19477)) |
| Equal word limits; the record puts the sides in random order | Judges prefer longer answers and favor position | Khan et al. 2024 ([arXiv 2402.06782](https://arxiv.org/abs/2402.06782)); Ma et al. 2025 |
| Always two sides, never a single advocate | Debate beat a lone consultant on every task tested; it lifted weak judges from 48% to 76% accuracy, and humans from 60% to 88% | Kenton et al. 2024 ([arXiv 2407.04622](https://arxiv.org/abs/2407.04622)); Khan et al. 2024 |
| The side against must argue a real rival plan | Assigned devil's advocacy is weaker than authentic dissent; building rival cases holds up better than picking holes | Nemeth, Brown, Rogers 2001 (doi 10.1002/ejsp.58, partly verified); Schweiger, Sandberg, Ragan 1986 (doi 10.5465/255859) |
| The judge writes hypotheses and a sealed prior before any argument | Anchoring on the first strong speaker; deciding before the evidence is laid out | Heuer, *Psychology of Intelligence Analysis*, ch. 8 (Analysis of Competing Hypotheses); the Mediating Assessments Protocol of Kahneman, Sibony and Lovallo |
| A premortem seat on every jury | Doubters stay quiet when a plan has momentum | Klein 2007, *Performing a Project Premortem*, HBR |
| Findings before votes, graded verified, plausible or assumption | Verdict driven deliberation covers less evidence than evidence driven deliberation | Hastie, Penrod, Pennington 1983, *Inside the Jury* |
| The judge weighs evidence, not headcount; minority views always reported | Jurors on one model share blind spots; in about one in four split cases the minority held the right answer | He et al. 2026, *Minority Sentinel* ([arXiv 2606.29270](https://arxiv.org/abs/2606.29270)); Ladha 1992 on correlated votes and the Condorcet jury theorem |
| Probability plus confidence per juror, median and spread in the tally | A single guilty or not guilty vote loses how sure each juror is | Mellers et al. 2014 and Satopää et al. 2014 on aggregating forecasts |
| The ruling says unanimity is weak when every juror shares a model | A panel from different model families beat one large judge with less bias | Verga et al. 2024, *Replacing Judges with Juries* ([arXiv 2404.18796](https://arxiv.org/abs/2404.18796)) |
| Step 1 sends checkable questions elsewhere | On questions with a right answer, majority voting explains most of the gain credited to debate | Choi, Zhu, Li 2025, *Debate or Vote* ([arXiv 2508.17536](https://arxiv.org/abs/2508.17536), NeurIPS 2025) |

## What is not proven
- No study tested a courtroom like this one end to end, and none tested Claude Code subagents. The rules are
  each grounded; the whole is a design.
- How many jurors is best for open decisions is unknown. Studies mostly use 3 to 5 agents.
- No tested prompt makes a judge immune to persuasion. Word limits, random order, a sealed prior and evidence
  grades reduce the known biases; they do not remove them.

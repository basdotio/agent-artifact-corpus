# What the research shows (verified 27 Sep 2026)

Cite from this file, not from memory. Every number below was checked against the primary source
on the date above. If you need a figure that isn't here, go to the paper and add it with the
section or table it came from.

## StoryScope: narrative choices separate AI fiction from human fiction

Russell, Rajendhran, Pham, Iyyer and Wieting (2026). *StoryScope: Investigating idiosyncrasies in
AI fiction.* [arXiv:2604.03136](https://arxiv.org/abs/2604.03136) (v6, 10 Aug 2026).
**Licence: CC0 1.0**, so figures can be reproduced (credit anyway).

- Corpus: 10,272 prompts, each written by a human author and five models (Claude, DeepSeek,
  Gemini, GPT, Kimi): 61,608 stories of about 5,000 words, 304 features per story.
- Detection from **narrative features alone** (no style): 93.2% macro-F1. Style only: 85.8%.
  Both: 96.0%. Text classifiers such as ModernBERT reach 99.9% (Table 2).
- After professional-style surface edits removed clichés and purple prose (the LAMP framework),
  narrative detection still scored 93.9%, down only 1.6 points from 95.5% (section 4.2).
- Six-way attribution (which model wrote it): 68.4% from narrative features, 77.3% with style
  (Table 3).
- AI stories cluster in one region of narrative space; human stories are more varied (mean
  rarity percentile 0.71 human vs 0.49 AI). Figure 2 shows it.
- Section 4.1, AI vs human share of stories:

| Narrative choice | AI | Human |
|---|---|---|
| Narrator explicitly explains the theme | 77% | 52% |
| Emotion shown through bodily sensation | 81% | 38% |
| Dialogue used for philosophical debate | 59% | 34% |
| References are vague allusions, not named works | 72% | 50% |
| No subplots at all | 79% | 57% |
| Resolution driven by the protagonist | 69% | 46% |
| Names specific texts and authors | 24% | 47% |
| Morally ambivalent protagonist | 38% | 59% |
| Breaks the fourth wall | 39% | 67% |
| Addresses the reader directly | 7% | 28% |
| Names emotions outright ("felt afraid") | 8% | 29% |

- Per-model fingerprints: Claude has notably flat event escalation, GPT leans on gossip as a plot
  device (v1 said dream sequences; v6 says gossip), Gemini defaults to external character
  description.
- **Limit:** this is fiction. The lesson that transfers is structural (over-explaining, tidy
  single-track arguments, resolved ambiguity), not a claim that marketing copy behaves the same.

## Readers, experts and fine-tuning

Chakrabarty, Ginsburg and Dhillon (2026). *Readers prefer outputs of AI trained on copyrighted
books over expert human writers.* [arXiv:2510.13939](https://arxiv.org/abs/2510.13939).

- MFA-trained writers vs ChatGPT, Claude and Gemini writing up to 450-word excerpts in the style
  of 50 award-winning authors, judged blind by 28 MFA-trained readers and 516 general readers.
- **Prompted** AI was strongly disfavoured by expert readers on quality (odds ratio 0.13) and
  stylistic fidelity (0.16). General readers showed no fidelity preference (1.06) and mildly
  favoured AI on quality (1.82).
- **Fine-tuned** on an author's complete works, AI was preferred by experts (quality 1.87,
  fidelity 8.16) and by general readers (quality 5.42, fidelity 16.65).
- Detectors flagged prompted output 97% of the time and fine-tuned output 3% of the time.
  Mediation analysis: fine-tuning removes the detectable quirks that penalised the prompted text.
- **Use it honestly:** the gap between prompted and expert writing is the quirks, and the quirks
  are fixable with the writer's own material. It is not evidence that AI copy is always worse.

## Homogenisation: individually better, collectively the same

Doshi and Hauser (2024). *Generative AI enhances individual creativity but reduces the collective
diversity of novel content.* Science Advances 10, eadn5290.
[doi:10.1126/sciadv.adn5290](https://doi.org/10.1126/sciadv.adn5290) ·
[PMC11244532](https://europepmc.org/article/PMC/PMC11244532).

- 293 writers, eight-sentence stories, three conditions: no AI, one AI idea, five AI ideas.
- Five AI ideas raised judged novelty by 8.1%. For the least creative writers: novelty +10.7%,
  "well written" up to +26.6%, enjoyment up to +22.6%.
- But AI-assisted stories were measurably more similar to each other (embedding similarity), a
  social dilemma: each writer is better off while the pool gets narrower.

[arXiv:2607.26899](https://arxiv.org/abs/2607.26899) (2026), *Human diversity fuels collective
creativity that large language models cannot simulate or sustain*: AI ideation compressed
collective diversity for every group; AI refining a writer's own ideas preserved it. Every
simulated persona pool scored below every human pool.

## Vocabulary: the words that gave it away

Kobak, González-Márquez, Horvát and Lause (2025). *Delving into LLM-assisted writing in biomedical
publications through excess vocabulary.* Science Advances 11(27), eadt3813.
[arXiv:2406.07016](https://arxiv.org/abs/2406.07016) · data and code:
[berenslab/llm-excess-vocab](https://github.com/berenslab/llm-excess-vocab) (**MIT**).

- 15 million+ PubMed abstracts, 2010 to 2024. At least 13.5% of 2024 abstracts were processed
  with an LLM, up to 40% in some subcorpora.
- Computed from their `results/yearly-counts.csv.gz` (abstracts containing the word, per 1,000):

| Word | 2022 | 2023 | 2024 |
|---|---|---|---|
| delves | 0.07 | 0.75 | 3.57 |
| showcasing | 0.17 | 0.52 | 2.29 |
| underscores | 1.04 | 2.92 | 14.39 |
| intricate | 1.34 | 3.26 | 9.92 |
| pivotal | 5.65 | 7.08 | 17.30 |
| notably | 12.22 | 16.47 | 35.25 |

- Word habits move with model releases; the StoryScope paper notes GPT-5.4 cut em-dash use. So
  word lists date quickly, and structure is the durable signal.

## Other useful sources

- Wikipedia, [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)
  (WikiProject AI Cleanup; CC BY-SA 4.0: paraphrase and attribute, never copy wholesale).
- Shaib et al. (2026), *Measuring AI "slop" in text*,
  [arXiv:2509.19163](https://arxiv.org/abs/2509.19163): a taxonomy of low-quality AI text;
  binary slop judgements are somewhat subjective but track coherence and relevance.
- Liang et al. (2024), *Monitoring AI-modified content at scale*,
  [arXiv:2403.07183](https://arxiv.org/abs/2403.07183): 6.5% to 16.9% of peer reviews at major AI
  conferences substantially LLM-modified.

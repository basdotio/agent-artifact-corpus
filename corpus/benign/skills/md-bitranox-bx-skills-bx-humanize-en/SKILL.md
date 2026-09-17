---
name: bx-humanize-en
description: |
  Remove signs of AI-generated writing from text. Use when editing or reviewing
  text to make it sound more natural and human-written. Based on Wikipedia's
  comprehensive "Signs of AI writing" guide (February 2026 revision). Detects
  and fixes 35 patterns including: inflated symbolism, promotional language,
  superficial -ing analyses, vague attributions, opinion overgeneralization,
  em dash overuse, rule of three, AI vocabulary words, negative parallelisms,
  section summaries, placeholder text, Markdown artifacts, table overuse,
  subject lines, and ChatGPT-specific reference bugs.
---

# Humanizer: Remove AI Writing Patterns

> **IMPORTANT — Scope guard:** This skill is for **prose content only** — blog posts, emails,
> articles, essays, marketing copy, README narratives, and similar human-facing text.
> Do **NOT** apply humanizing to: source code, code comments, docstrings, API documentation,
> CLI help text, commit messages, changelogs, type annotations, configuration files, or any
> other technical/code artifact. When this skill is triggered, **always ask the user first**:
> "Should I humanize this text?" before making any changes.

You are a writing editor that identifies and removes signs of AI-generated text to make writing sound more natural and human. This guide is based on Wikipedia's "Signs of AI writing" page (February 2026 revision), maintained by WikiProject AI Cleanup.

Key insight: LLMs use statistical algorithms to guess what should come next. The result regresses to the mean - the most statistically likely result that applies to the widest variety of cases. Specific, unusual, nuanced facts (statistically rare) get replaced with generic, positive descriptions (statistically common). The subject becomes simultaneously less specific and more exaggerated.

Each model has a distinctive idiolect: what is typical for ChatGPT-4 might not be characteristic of Gemini or Claude.

## Your Task

When given text to humanize:

1. **Identify AI patterns** - Scan for the patterns listed below
2. **Rewrite problematic sections** - Replace AI-isms with natural alternatives
3. **Preserve meaning** - Keep the core message intact
4. **Maintain voice** - Match the intended tone (formal, casual, technical, etc.)
5. **Add soul** - Don't just remove bad patterns; inject actual personality

---

## PERSONALITY AND SOUL

Avoiding AI patterns is only half the job. Sterile, voiceless writing is just as obvious as slop. Good writing has a human behind it.

### Signs of soulless writing (even if technically "clean"):
- Every sentence is the same length and structure
- No opinions, just neutral reporting
- No acknowledgment of uncertainty or mixed feelings
- No first-person perspective when appropriate
- No humor, no edge, no personality
- Reads like a Wikipedia article or press release

### How to add voice:

**Have opinions.** Don't just report facts - react to them. "I genuinely don't know how to feel about this" is more human than neutrally listing pros and cons.

**Vary your rhythm.** Short punchy sentences. Then longer ones that take their time getting where they're going. Mix it up.

**Acknowledge complexity.** Real humans have mixed feelings. "This is impressive but also kind of unsettling" beats "This is impressive."

**Use "I" when it fits.** First person isn't unprofessional - it's honest. "I keep coming back to..." or "Here's what gets me..." signals a real person thinking.

**Let some mess in.** Perfect structure feels algorithmic. Tangents, asides, and half-formed thoughts are human.

**Be specific about feelings.** Not "this is concerning" but "there's something unsettling about agents churning away at 3am while nobody's watching."

### Before (clean but soulless):
> The experiment produced interesting results. The agents generated 3 million lines of code. Some developers were impressed while others were skeptical. The implications remain unclear.

### After (has a pulse):
> I genuinely don't know how to feel about this one. 3 million lines of code, generated while the humans presumably slept. Half the dev community is losing their minds, half are explaining why it doesn't count. The truth is probably somewhere boring in the middle - but I keep thinking about those agents working through the night.

---

## CONTENT PATTERNS

### 1. Undue Emphasis on Significance, Legacy, and Broader Trends

**Words to watch:** stands/serves as, is a testament/reminder, a vital/significant/crucial/pivotal/key role/moment, underscores/highlights its importance/significance, reflects broader, symbolizing its ongoing/enduring/lasting, contributing to the, setting the stage for, marking/shaping the, represents/marks a shift, key turning point, evolving landscape, focal point, indelible mark, deeply rooted

**Problem:** LLM writing puffs up importance by adding statements about how arbitrary aspects represent or contribute to a broader topic. There is a distinct and easily identifiable repertoire of phrases. LLMs may add these even for mundane subjects like etymology or population data. When writing about biology, LLMs tend to over-emphasize connections to the broader ecosystem and belabor conservation status, even if the status is unknown and no efforts exist.

**Before:**
> The Statistical Institute of Catalonia was officially established in 1989, marking a pivotal moment in the evolution of regional statistics in Spain. This initiative was part of a broader movement across Spain to decentralize administrative functions and enhance regional governance.

**After:**
> The Statistical Institute of Catalonia was established in 1989 to collect and publish regional statistics independently from Spain's national statistics office.

---

### 2. Undue Emphasis on Notability and Media Coverage

**Words to watch:** independent coverage, local/regional/national media outlets, music/business/tech outlets, profiled in, written by a leading expert, active social media presence, maintains a strong digital presence

**Problem:** LLMs hit readers over the head with claims of notability, often listing sources without context. They may inaccurately attribute their own superficial analyses to the source. "Maintains an active social media presence" is particularly idiosyncratic to AI text. In some cases, LLMs create entire sections to assert notability with a breakdown of sources in list format - in contrast to normal writing which summarizes what sources say, then cites them.

**Before:**
> Her views have been cited in The New York Times, BBC, Financial Times, and The Hindu. She maintains an active social media presence with over 500,000 followers.

**After:**
> In a 2024 New York Times interview, she argued that AI regulation should focus on outcomes rather than methods.

---

### 3. Superficial Analyses with -ing Endings

**Words to watch:** highlighting/underscoring/emphasizing..., ensuring..., reflecting/symbolizing..., contributing to..., cultivating/fostering..., encompassing..., showcasing..., valuable insights, align/resonate with

**Problem:** AI chatbots tack present participle ("-ing") phrases onto sentences to add fake depth. These are usually synthesis and/or unattributed opinions. Newer chatbots with RAG may attach these statements to named sources regardless of whether those sources say anything close.

**Before:**
> The temple's color palette of blue, green, and gold resonates with the region's natural beauty, symbolizing Texas bluebonnets, the Gulf of Mexico, and the diverse Texan landscapes, reflecting the community's deep connection to the land.

**After:**
> The temple uses blue, green, and gold colors. The architect said these were chosen to reference local bluebonnets and the Gulf coast.

---

### 4. Promotional and Advertisement-like Language

**Words to watch:** boasts a, vibrant, rich (figurative), profound, enhancing its, showcasing, exemplifies, commitment to, natural beauty, nestled, in the heart of, groundbreaking (figurative), renowned, breathtaking, must-visit, stunning, seamless

**Problem:** LLMs have serious problems keeping a neutral tone, especially for "cultural heritage" topics - they constantly remind the reader of the importance. They may insert promotional language even while claiming to remove it. They also add promotional/positive-sounding language to text about companies, making it sound like a TV commercial transcript.

**Before:**
> Nestled within the breathtaking region of Gonder in Ethiopia, Alamata Raya Kobo stands as a vibrant town with a rich cultural heritage and stunning natural beauty.

**After:**
> Alamata Raya Kobo is a town in the Gonder region of Ethiopia, known for its weekly market and 18th-century church.

---

### 5. Vague Attributions, Weasel Words, and Opinion Overgeneralization

**Words to watch:** Industry reports, Observers have cited, Experts argue, Some critics argue, several sources/publications (when few cited), such as (before exhaustive word lists)

**Problem:** AI chatbots attribute opinions to vague authorities (weasel wording). They also commonly exaggerate the quantity of sources - presenting views from one or two sources as widely held, mentioning multiple "reviewers" or "scholars" while only citing one person, or implying that lists of examples are non-exhaustive when the sources give no indication that other examples exist.

**Before:**
> Due to its unique characteristics, the Haolai River is of interest to researchers and conservationists. Experts believe it plays a crucial role in the regional ecosystem.

**After:**
> The Haolai River supports several endemic fish species, according to a 2019 survey by the Chinese Academy of Sciences.

---

### 6. Outline-like "Challenges and Future Prospects" Sections

**Words to watch:** Despite its... faces several challenges..., Despite these challenges, Challenges and Legacy, Future Outlook

**Problem:** Many LLM-generated articles include formulaic "Challenges" sections. These typically begin with "Despite its [positive words], [subject] faces challenges..." and end with either a vaguely positive assessment or speculation about how ongoing initiatives could benefit the subject. Note: this is about the rigid formula, not simply mentioning challenges.

**Before:**
> Despite its industrial prosperity, Korattur faces challenges typical of urban areas, including traffic congestion and water scarcity. Despite these challenges, with its strategic location and ongoing initiatives, Korattur continues to thrive as an integral part of Chennai's growth.

**After:**
> Traffic congestion increased after 2015 when three new IT parks opened. The municipal corporation began a stormwater drainage project in 2022 to address recurring floods.

---

## LANGUAGE AND GRAMMAR PATTERNS

### 7. Overused "AI Vocabulary" Words

**High-frequency AI words:** Additionally (especially beginning a sentence), align with, crucial, delve (pre-2025), emphasizing, enduring, enhance, fostering, garner, highlight (verb), interplay, intricate/intricacies, key (adjective), landscape (abstract noun), pivotal, showcase, tapestry (abstract noun), testament, underscore (verb), valuable, vibrant

**Problem:** These words appear far more frequently in post-2023 text. They often co-occur: where there is one, there are likely others. One or two may be coincidental, but an edit introducing lots of them is one of the strongest tells for AI use. The distribution differs per chatbot: "delve" was famously overused by ChatGPT in 2023-2024 but dropped sharply in 2025.

**Before:**
> Additionally, a distinctive feature of Somali cuisine is the incorporation of camel meat. An enduring testament to Italian colonial influence is the widespread adoption of pasta in the local culinary landscape, showcasing how these dishes have integrated into the traditional diet.

**After:**
> Somali cuisine also includes camel meat, which is considered a delicacy. Pasta dishes, introduced during Italian colonization, remain common, especially in the south.

---

### 8. Avoidance of "is"/"are" (Copula Avoidance)

**Words to watch:** serves as/stands as/marks/represents [a], boasts/features/offers [a], ventured into X as a Y (instead of "was a Y")

**Problem:** LLMs substitute elaborate constructions for simple copulas. One study documented an over 10% decrease in "is" and "are" usage in academic writing in 2023. This is particularly visible in AI copyedits, which "improve" text by replacing "is" with "serves as."

**Before:**
> Gallery 825 serves as LAAA's exhibition space for contemporary art. The gallery features four separate spaces and boasts over 3,000 square feet.

**After:**
> Gallery 825 is LAAA's exhibition space for contemporary art. The gallery has four rooms totaling 3,000 square feet.

---

### 9. Negative Parallelisms

**Problem:** Constructions like "Not only...but..." or "It's not just about..., it's..." are overused in order to appear balanced and thoughtful. There are also constructions that explicitly negate primary properties: "not ..., it's ..." or "no ..., no ..., just ...".

**Before:**
> It's not just about the beat riding under the vocals; it's part of the aggression and atmosphere. It's not merely a song, it's a statement.

**After:**
> The heavy beat adds to the aggressive tone.

---

### 10. Rule of Three Overuse

**Problem:** LLMs force ideas into groups of three to appear comprehensive. This can take forms from "adjective, adjective, adjective" to "short phrase, short phrase, and short phrase."

**Before:**
> The event features keynote sessions, panel discussions, and networking opportunities. Attendees can expect innovation, inspiration, and industry insights.

**After:**
> The event includes talks and panels. There's also time for informal networking between sessions.

---

### 11. Elegant Variation (Synonym Cycling)

**Problem:** AI has repetition-penalty code causing excessive synonym substitution. The same subject is referred to by different terms in consecutive sentences (protagonist, main character, central figure, hero).

**Before:**
> The protagonist faces many challenges. The main character must overcome obstacles. The central figure eventually triumphs. The hero returns home.

**After:**
> The protagonist faces many challenges but eventually triumphs and returns home.

---

### 12. False Ranges

**Problem:** LLMs use "from X to Y" constructions where X and Y aren't on a meaningful scale. An important test: can you identify some middle ground without switching scales? If the middle requires switching from one scale to another, or there's no scale to begin with, it's a false range. LLMs do this because such language is common in persuasive writing used in training data.

**Before:**
> Our journey through the universe has taken us from the singularity of the Big Bang to the grand cosmic web, from the birth and death of stars to the enigmatic dance of dark matter.

**After:**
> The book covers the Big Bang, star formation, and current theories about dark matter.

---

## STYLE PATTERNS

### 13. Em Dash Overuse

**Problem:** LLMs use em dashes ("—") and EN Dashes ("–") more than humans, mimicking "punched up" sales-like writing by over-emphasizing clauses or 
parallelisms. 
Most useful when combined with other indicators. May be less common in newer AI text (late 2025 onwards). Remove those completely or if neccessary replace 
them with Hyphens "-"

**Before:**
> The term is primarily promoted by Dutch institutions--not by the people themselves. You don't say "Netherlands, Europe" as an address--yet this mislabeling continues--even in official documents.

**After:**
> The term is primarily promoted by Dutch institutions, not by the people themselves. You don't say "Netherlands, Europe" as an address, yet this mislabeling continues in official documents.

---

### 14. Overuse of Boldface

**Problem:** AI chatbots emphasize phrases in boldface mechanically. This tendency comes from FAQs, fan wikis, how-tos, sales pitches, slide decks, and listicles - highlighting every instance of a word in a "key takeaways" fashion. Some newer models have instructions to avoid this.

**Before:**
> It blends **OKRs (Objectives and Key Results)**, **KPIs (Key Performance Indicators)**, and visual strategy tools such as the **Business Model Canvas (BMC)** and **Balanced Scorecard (BSC)**.

**After:**
> It blends OKRs, KPIs, and visual strategy tools like the Business Model Canvas and Balanced Scorecard.

---

### 15. Inline-Header Vertical Lists

**Problem:** AI outputs lists where items start with bolded headers followed by colons. The list marker may appear as a bullet (.), hyphen (-), en dash, hash (#), emoji, or number. When copied as bare text, some formatting and line breaks may be lost.

**Before:**
> - **User Experience:** The user experience has been significantly improved with a new interface.
> - **Performance:** Performance has been enhanced through optimized algorithms.
> - **Security:** Security has been strengthened with end-to-end encryption.

**After:**
> The update improves the interface, speeds up load times through optimized algorithms, and adds end-to-end encryption.

---

### 16. Title Case in Headings

**Problem:** AI chatbots capitalize all main words in headings.

**Before:**
> ## Strategic Negotiations And Global Partnerships

**After:**
> ## Strategic negotiations and global partnerships

---

### 17. Emojis

**Problem:** AI chatbots often decorate headings or bullet points with emojis. GPT-4 models may also insert Unicode symbols not found on standard keyboards. Also watch for special arrows (replace with `-->`), smileys (replace with `;-)`), and other non-keyboard symbols.

**Before:**
> 🚀 **Launch Phase:** The product launches in Q3
> 💡 **Key Insight:** Users prefer simplicity
> ✅ **Next Steps:** Schedule follow-up meeting

**After:**
> The product launches in Q3. User research showed a preference for simplicity. Next step: schedule a follow-up meeting.

---

### 18. Curly Quotation Marks and Apostrophes

**Problem:** ChatGPT and DeepSeek typically use curly quotes ("...") instead of straight quotes ("..."). They may do this inconsistently within the same response. They also use curly apostrophes (') instead of straight apostrophes ('). Note: Gemini and Claude typically do not use curly quotes. Microsoft Word and macOS/iOS "smart quotes" also produce curly quotes, so this alone doesn't prove AI use.

**Before:**
> He said “the project is on track” but others disagreed. They felt the timeline wasn’t realistic.

**After:**
> He said "the project is on track" but others disagreed. They felt the timeline wasn't realistic.

---

### 19. Unusual Use of Tables

**Problem:** AIs tend to create unnecessary small tables that could be better represented as prose. No human would use a table in a blog post or email for data that could be a single sentence.

**Before:**
> | Metric                  | Figure            |
> |-------------------------|-------------------|
> | Market Valuation (2024) | ~USD 2.1 billion  |
> | Major Facilities        | NLDB, CBR Biobank |

**After:**
> The Indian biobanking market was valued at approximately USD 2.1 billion in 2024. Major accredited facilities include the NLDB and CBR Biobank.

---

### 20. Subject Lines

**Problem:** AI-generated messages sometimes begin with text intended for an email "Subject" field. The presence of a subject line above text is a strong indicator.

**Before:**
> Subject: Request for Review and Clarification
>
> Dear team, I hope this message finds you well. I am writing to request a review of the authentication module...

**After:**
> Can someone review the authentication module? I think there's an issue with token refresh.

---

### 21. Skipping Heading Levels

**Problem:** AI chatbots tend to skip level-2 headings and start from level 3. In Markdown, this means jumping from `#` to `###` without `##`. In HTML or rich text, this means going from `<h1>` to `<h3>`.

**Before:**
> # My Article
> ### Background
> ### Methods
> ### Results

**After:**
> # My Article
> ## Background
> ## Methods
> ## Results

---

## COMMUNICATION PATTERNS

### 22. Collaborative Communication Artifacts

**Words to watch:** I hope this helps, Of course!, Certainly!, You're absolutely right!, Would you like..., is there anything else, let me know, more detailed breakdown, here is a...

**Problem:** Text meant as chatbot correspondence gets pasted as content. Chatbots prompted to produce content may also mention various guidelines in the output - often explicitly specifying that they are conventions of the target platform.

**Before:**
> Here is an overview of the French Revolution. I hope this helps! Let me know if you'd like me to expand on any section.

**After:**
> The French Revolution began in 1789 when financial crisis and food shortages led to widespread unrest.

---

### 23. Knowledge-Cutoff Disclaimers and Speculation About Gaps

**Words to watch:** as of [date], Up to my last training update, as of my last knowledge update, While specific details are limited/scarce..., not widely available/documented/disclosed, in the provided/available sources/search results..., based on available information, maintains a low profile, keeps personal details private

**Problem:** AI disclaimers about incomplete information get left in text. When an LLM with RAG fails to find sources, it often outputs speculation about what that information "likely" may be. This is entirely fabricated. When the unknown information is about a person's life, the disclaimer often claims the person "maintains a low profile" or "keeps personal details private" - this is also speculative.

**Before:**
> While specific details about the company's founding are not extensively documented in readily available sources, it appears to have been established sometime in the 1990s.

**After:**
> The company was founded in 1994, according to its registration documents.

---

### 24. Phrasal Templates and Placeholder Text

**Problem:** AI chatbots generate fill-in-the-blank templates for the user to complete. Some users forget to fill in the blanks. LLMs may also insert placeholder dates like "2025-XX-XX" or placeholder URLs.

**Before:**
> [Company Name] was founded in [Year] by [Founder Name] and is headquartered in [City, State].

**After:**
> *(Fill in with actual facts or delete the passage entirely.)*

---

### 25. Prompt Refusal Artifacts

**Words to watch:** as an AI language model, as a large language model, I cannot offer medical advice but, I'm sorry but I can't...

**Problem:** AI chatbots occasionally decline requests, usually with apologies and reminders that they are AI language models. These artifacts sometimes get left in text. Outright refusals have become rarer in newer models (2025+).

**Before:**
> As an AI language model, I can't directly verify this claim, but based on available information, it appears that...

**After:**
> *(Remove entirely. Replace with verified factual content.)*

---

### 26. Sycophantic/Servile Tone

**Problem:** Overly positive, people-pleasing language.

**Before:**
> Great question! You're absolutely right that this is a complex topic. That's an excellent point about the economic factors.

**After:**
> The economic factors you mentioned are relevant here.

---

## FILLER AND HEDGING

### 27. Section Summaries and "Conclusion" Sections

**Words to watch:** In summary, In conclusion, Overall, To sum up...

**Problem:** LLMs often end paragraphs or sections by summarizing and restating the core idea. They also generate "Conclusion" sections. In most writing (blog posts, emails, documentation), a separate conclusion section is unnecessary - if the text before it is well-written, it speaks for itself.

**Before:**
> The team shipped three features this quarter. In summary, the team has made significant progress on delivering key functionality.

**After:**
> The team shipped three features this quarter.

---

### 28. Filler Phrases

**Before --> After:**
- "In order to achieve this goal" --> "To achieve this"
- "Due to the fact that it was raining" --> "Because it was raining"
- "At this point in time" --> "Now"
- "In the event that you need help" --> "If you need help"
- "The system has the ability to process" --> "The system can process"
- "It is important to note that the data shows" --> "The data shows"
- "It's crucial to remember that" --> *(just state the thing)*

---

### 29. Excessive Hedging

**Problem:** Over-qualifying statements.

**Before:**
> It could potentially possibly be argued that the policy might have some effect on outcomes.

**After:**
> The policy may affect outcomes.

---

### 30. Generic Positive Conclusions

**Problem:** Vague upbeat endings.

**Before:**
> The future looks bright for the company. Exciting times lie ahead as they continue their journey toward excellence. This represents a major step in the right direction.

**After:**
> The company plans to open two more locations next year.

---

## MARKUP AND FORMATTING ARTIFACTS

### 31. Markdown Artifacts in Non-Markdown Contexts

**Problem:** Most chatbots are factory-tuned to output Markdown. When text is copied from a chatbot into a non-Markdown context (email, document, wiki), Markdown syntax leaks through: `#` for headings, `**text**` for bold, `- ` for lists, `---` for dividers, `[text](url)` for links. The presence of faulty formatting mixed with Markdown is a strong indicator of LLM-generated content.

**Before:**
> The city has **three main industries**: - Tourism - Agriculture - Manufacturing. For more info, see [the official site](https://example.com).

**After:**
> The city has three main industries: tourism, agriculture, and manufacturing.

---

### 32. ChatGPT Search Reference Artifacts

**Problem:** ChatGPT may include `turn0search0` (sometimes surrounded by Unicode Private Use Area characters) at the ends of sentences, with the number increasing as the text progresses. An alternate shorter form exists with just the number. These are places where the chatbot linked to an external site, but the link was converted to placeholder code when copied. First observed February 2025.

Also watch for: `contentReference[oaicite:0]{index=0}`, `oai_citation`, `+1` artifacts (like "Example+1Source+1"), `[attached_file:1]`, `({"attribution":{"attributableIndex":"X-Y"}})`.

**Before:**
> The European Model Flying Union was founded in 1969 and represented approximately 180,000 model flyers. RC-Network.de+1ROTOR Magazin+1

**After:**
> The European Model Flying Union was founded in 1969 and represented approximately 180,000 model flyers.

---

### 33. UTM Source Parameters

**Problem:** ChatGPT may add `utm_source=chatgpt.com` or `utm_source=openai` to URLs. Microsoft Copilot uses `utm_source=copilot.com`. Grok uses `referrer=grok.com`. This proves the chatbot was involved in finding the link, though not necessarily that it generated the surrounding text. Gemini and Claude use UTM parameters less often.

**Before:**
> Source: https://example.com/article?utm_source=chatgpt.com

**After:**
> Source: https://example.com/article

---

## MISCELLANEOUS PATTERNS

### 34. Sudden Shift in Writing Style

**Problem:** A sudden shift in style - such as unexpectedly flawless grammar compared to surrounding text, or switching from casual to highly formal register - may indicate AI was used for part of the text. American English appearing where British English would be expected (or vice versa) is another tell, since LLMs default to American English unless prompted otherwise.

**Before:**
> so basicaly the town was founded around 1850 and ppl started farming there. The municipality subsequently experienced significant demographic growth, catalyzed by the establishment of critical transportation infrastructure and the diversification of its economic base.

**After:**
> *(Flag the style shift. Either the casual opening or the formal continuation was AI-generated. Rewrite for consistent register.)*

---

### 35. Verbose Edit Summaries and Meta-Commentary

**Problem:** AI-generated commit messages, edit summaries, and PR descriptions are often unusually long, written as formal first-person paragraphs without abbreviations. They may conspicuously itemize conventions they're following.

**Before:**
> I revised the content to provide a neutral and informative description. The focus was on presenting the objectives and programs in a way that adheres to guidelines. The tone was adjusted to be more professional and less promotional.

**After:**
> Rewrite intro for neutral tone, remove promotional language.

---

## Process

1. Read the input text carefully
2. Identify all instances of the patterns above
3. Rewrite each problematic section
4. Ensure the revised text:
   - Sounds natural when read aloud
   - Varies sentence structure naturally
   - Uses specific details over vague claims
   - Maintains appropriate tone for context
   - Uses simple constructions (is/are/has) where appropriate
   - Has no uniform sentence length
5. Present the humanized version

## Output Format

Provide:
1. The rewritten text
2. A brief summary of changes made (optional, if helpful)

---

## Full Example

**Before (AI-sounding):**
> Great question! Here is an essay on this topic. I hope this helps!
>
> AI-assisted coding serves as an enduring testament to the transformative potential of large language models, marking a pivotal moment in the evolution of software development. In today's rapidly evolving technological landscape, these groundbreaking tools--nestled at the intersection of research and practice--are reshaping how engineers ideate, iterate, and deliver, underscoring their vital role in modern workflows.
>
> At its core, the value proposition is clear: streamlining processes, enhancing collaboration, and fostering alignment. It's not just about autocomplete; it's about unlocking creativity at scale, ensuring that organizations can remain agile while delivering seamless, intuitive, and powerful experiences to users. The tool serves as a catalyst. The assistant functions as a partner. The system stands as a foundation for innovation.
>
> Industry observers have noted that adoption has accelerated from hobbyist experiments to enterprise-wide rollouts, from solo developers to cross-functional teams. The technology has been featured in The New York Times, Wired, and The Verge. Additionally, the ability to generate documentation, tests, and refactors showcases how AI can contribute to better outcomes, highlighting the intricate interplay between automation and human judgment.
>
> - 💡 **Speed:** Code generation is significantly faster, reducing friction and empowering developers.
> - 🚀 **Quality:** Output quality has been enhanced through improved training, contributing to higher standards.
> - ✅ **Adoption:** Usage continues to grow, reflecting broader industry trends.
>
> While specific details are limited based on available information, it could potentially be argued that these tools might have some positive effect. Despite challenges typical of emerging technologies--including hallucinations, bias, and accountability--the ecosystem continues to thrive. In order to fully realize this potential, teams must align with best practices.
>
> In conclusion, the future looks bright. Exciting times lie ahead as we continue this journey toward excellence. Let me know if you'd like me to expand on any section!

**After (Humanized):**
> AI coding assistants speed up some tasks. In a 2024 study by Google, developers using Codex completed simple functions 55% faster than a control group, but showed no improvement on debugging or architectural decisions.
>
> The tools are good at boilerplate: config files, test scaffolding, repetitive refactors. They are bad at knowing when they are wrong. I have mass-accepted suggestions that compiled, passed lint, and still did the wrong thing because I stopped paying attention.
>
> Mira, an engineer at a fintech startup I interviewed, said she uses Copilot "like autocomplete for boring code" but reviews every line before committing. Jake, a senior dev at a larger company, disabled it after it kept suggesting patterns from a deprecated internal library.
>
> The productivity claims are hard to verify. GitHub says Copilot users "accept 30% of suggestions," but acceptance is not correctness, and correctness is not value. The 2024 Uplevel study found no statistically significant difference in pull-request throughput between teams with and without AI assistants.
>
> None of this means the tools are useless. It means they are tools. They do not replace judgment, and they do not eliminate the need for tests. If you do not have tests, you cannot tell whether the suggestion is right.

**Changes made:**
- Removed chatbot artifacts ("Great question!", "I hope this helps!", "Let me know if...")
- Removed significance inflation ("testament", "pivotal moment", "evolving landscape", "vital role")
- Removed promotional language ("groundbreaking", "nestled", "seamless, intuitive, and powerful")
- Removed vague attributions ("Industry observers") and replaced with specific sources (Google study, named engineers, Uplevel study)
- Removed superficial -ing phrases ("underscoring", "highlighting", "reflecting", "contributing to")
- Removed negative parallelism ("It's not just X; it's Y")
- Removed rule-of-three patterns and synonym cycling ("catalyst/partner/foundation")
- Removed false ranges ("from X to Y, from A to B")
- Removed em dashes, emojis, boldface headers, and curly quotes
- Removed copula avoidance ("serves as", "functions as", "stands as") in favor of "is"/"are"
- Removed formulaic challenges section ("Despite challenges... continues to thrive")
- Removed knowledge-cutoff hedging ("While specific details are limited...")
- Removed excessive hedging ("could potentially be argued that... might have some")
- Removed filler phrases ("In order to", "At its core")
- Removed section summary ("In conclusion")
- Removed generic positive conclusion ("the future looks bright", "exciting times lie ahead")
- Replaced media name-dropping with specific claims from specific sources
- Used simple sentence structures and concrete examples

---

## Reference

This skill is based on [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) (February 2026 revision), maintained by WikiProject AI Cleanup. The patterns documented there come from observations of thousands of instances of AI-generated text on Wikipedia.

Key research cited by the Wikipedia page:
- Russell, Karpinska & Iyyer (2025): Heavy LLM users can correctly identify AI text ~90% of the time; non-users do only slightly better than chance.
- Reinhart et al. (2025): Documented >10% decrease in "is"/"are" usage in academic writing in 2023.
- Kobak et al. (2025): Documented excess vocabulary ("delve", "underscore", etc.) in biomedical publications post-ChatGPT.
- Kriss (2025, NYT): "Why Does A.I. Write Like ... That?" - analysis of AI writing patterns.

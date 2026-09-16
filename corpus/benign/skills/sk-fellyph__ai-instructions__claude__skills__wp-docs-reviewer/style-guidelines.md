# Style Guidelines Reference

Comprehensive reference for voice, tone, accessibility, inclusivity, and general writing standards in WordPress documentation.

## Table of Contents

1. [Voice and Tone](#voice-and-tone)
2. [Accessibility](#accessibility)
3. [Inclusivity](#inclusivity)
4. [Global Audience](#global-audience)
5. [Document Structure](#document-structure)
6. [Facts and Claims](#facts-and-claims)

## Voice and Tone

### Core Principles

- **Conversational yet professional**: Balance between casual and formal
- **Succinct and natural**: Clear, direct communication
- **Friendly toward the reader**: Welcoming and supportive
- **Reader-focused**: Emphasize "you" not "we"

### Things to Avoid

- Colloquial/idiomatic expressions
- Unnecessary metaphors or humor
- Cultural and regional references
- Technical jargon without explanation
- Shortcuts and unexplained abbreviations
- Being overly pretentious
- Dictating or commanding tone ("You must...", "You need to...")
- Being overly polite ("Please click...")
- Excessive exclamation points
- Unnecessary capitalization
- Same phrases/pronouns repeated excessively
- Ableist language
- Long, complicated sentences
- Assumptions about reader's knowledge
- Heavily biased information

### Things to Encourage

- Second person ("you")
- Active voice
- Present tense
- Contractions (they've, don't)
- Brief, concise sentences
- Conditional phrases
- Defining technical terms
- Transition words (moreover, although, hence)
- Proof-reading for tone

### Tone by Documentation Type

**End-user documentation**:
- Friendly, informal tone
- Clear and concise
- Get to point promptly
- Explain technical terms without condescension
- Brief context at start

**Developer documentation**:
- Direct and precise
- Assume higher technical knowledge
- Still maintain clarity
- For code reference: be as direct as possible

### Examples

**Not Recommended**:
> If you peek over at the left side, you'll see a menu called main navigation, which is the main menu.

**Recommended**:
> On the left side is the **Main navigation menu** listing the administrative functions.

**Not Recommended**:
> When you visit a website, you probably want the website to remember some information about you so you don't have to give it the information again. Websites can send your browser this kind of information so they remember you later. This information is called a cookie. I know what you're thinking, a cookie is something you eat, right? Well, a computer cookie is different.

**Recommended**:
> A cookie is a small piece of data used to remember information about you. When you visit a website, it sends a cookie to your browser, and your browser stores the cookie in a small file.

## Accessibility

### General Principles

- Emphasize the reader, not their disabilities
- Use approved disability terminology
- Maintain uniform document structure
- Test with screen readers
- Consider multi-platform accessibility
- Document all input device types
- Avoid ableist language
- Use proper HTML semantics
- Keep tables simple

### Text Accessibility

**Requirements**:
- Concise, simple sentences
- Avoid camel case and all caps
- Proper heading hierarchy (H1 → H6, no skipping)
- No decorative fonts
- No shaded backgrounds or watermarks
- Break text into paragraphs
- Define abbreviations and acronyms
- Indicate when links open in new tabs

**Heading Structure**:
- H1 = page title (one per page)
- H2-H6 = subsections
- Don't skip levels
- No extra functionality in headings (no links/buttons inside)

**Contrast and Color**:
- Minimum contrast ratio: 4.5:1
- Don't rely solely on color to convey information
- Test without color

### Media Accessibility

**Images**:
- Provide alt text (limit 50 characters)
- Include `figure` tags where appropriate
- Use actual text, not images of text

**Audio/Video**:
- Provide transcripts
- Include closed captions
- Add descriptions
- Provide controls (no auto-play)

**Animations**:
- No flickering or flashing (seizure risk)
- Provide pause controls

### UI Accessibility

- Don't use direction-only navigation ("on the right")
- Clearly state error descriptions and fixes
- Use correct UI element terminology
- Reference elements by their `aria-label`

### Document Rendering

Consider viewing in:
- Multiple device sizes
- Without sound
- Using only sound
- Without color
- With keyboard only
- With screen magnification
- Without punctuation

## Inclusivity

### Core Commitment

WordPress documentation is welcoming and inclusive of people of all demographics.

### Unbiased Documentation

- Inclusive of all gender identities, races, cultures, abilities, ages, sexual orientations, socioeconomic classes
- Avoid politicized content (or remain neutral)
- Follow accessibility guidelines
- No content that insults or harms
- No generalizations about people, countries, cultures
- No prejudiced content against minorities
- Avoid terms related to historical events (when problematic)

### Replacing Established Terms

When non-inclusive terms must be mentioned, use parenthetical reference only on first use:

**Examples**:
- "If `disallowed_keys` (previously known as `blacklist_keys`) exists..."
- "The comment blocklist (sometimes called a *blacklist*) shows blocked comments"

### Terminology Changes

| Recommended | Not Recommended |
|-------------|-----------------|
| deny list, blocklist, disallowed, unapproved | blacklist |
| allowlist, allowed, approved | whitelist |
| main | master |
| primary/subordinate | master/slave |
| site admin, web developer | webmaster |
| built-in, core | native |

### Gender-Neutral Language

**Pronouns**:
- Use "they/their/them" for singular individuals
- When writing about real individuals, use their preferred pronouns
- Avoid gendered pronouns unless specifically preferred

**Terms to Replace**:
| Recommended | Not Recommended |
|-------------|-----------------|
| human-power, staff, personnel, workforce | manpower |
| humankind, humanity, people | man, mankind |
| operates, controls, utilizes | mans |
| manufactured | manmade |
| chairperson | chairman |
| everyone, folks, people | guys, gals, girls, boys |

**Writing Around Pronouns**:
1. Rewrite using second person (you)
2. Use plural nouns and pronouns
3. Use "person" or "individual"
4. Use articles (the, an, a)
5. Use plural "they" for singular

### Diverse Examples

- Represent diverse perspectives in examples
- Use inclusive range of:
  - Names (various cultural origins)
  - Ages
  - Gender identities
  - Locations (global)
  - Professions
  - Cultures
- Avoid generalizations about religions, cultures, regions, countries
- Avoid unintentional racial/cultural bias

### Accessibility and Disability

**Terminology**:
| Recommended | Not Recommended |
|-------------|-----------------|
| person with disability | the disabled, handicapped, differently abled, challenged, abnormal |
| person without disability | normal person, healthy person, able-bodied |
| has [disability] | victim of, suffering from, affected by, stricken with |
| unable to speak, uses synthetic speech | dumb, mute |
| deaf, low-hearing | hearing-impaired |
| blind, low-vision | vision-impaired, visually-challenged |
| cognitive or developmental disabilities | mentally-challenged, slow-learner |
| person with limited mobility, person with a physical disability | crippled, handicapped |

**Approach**:
- Research preferred terminology
- Don't refer to people without disabilities as "normal, fit, healthy"
- Don't use judgmental terms that victimize

## Global Audience

### Internationalization Considerations

WordPress is used globally, with ~50% of installs in non-English locales. Write considering translation.

### Language Guidelines

**Sentence Structure**:
- Concise, succinct sentences
- Simple verbs and vocabulary
- Break complex sentences into multiple sentences
- Replace complex paragraphs with illustrations, tables, lists

**Clarity**:
- Use abundant articles (a, an, the)
- Use helper words (if, then)
- Avoid shortcuts and symbols
- Ensure consistency in terminology
- Use consistent formatting

**Cultural Considerations**:
- No culturally-specific references
- Avoid colloquialisms, slang, idioms
- No pop culture references
- Avoid cultural practices, traditions, holidays, seasons
- No culturally-specific humor

### Standards

**Spelling**: American English
- color (not colour)
- optimize (not optimise)

**Date Format**: Month DD, YYYY
- October 28, 2025 (not 28/10/2025)

**Numbers**:
- Spell out one through nine
- Use numerals for 10+
- "Fewer" for countable items, "less" for accumulating things

**Time**:
- Local time for in-person events
- UTC for online events and regular meetings

**Measurements**:
- Use international standards
- Consider that units vary globally

## Document Structure

### Requirements

- Don't write walls of text
- Follow defined structure
- Break into paragraphs, lists, illustrations
- Use proper heading hierarchy
- Maintain uniform structure
- Emphasize important points visually and stylistically

### Text Formatting

- Consistent typography and font sizes
- Bold for emphasis and UI elements
- Italics for names, terminology

### Encoding

- Use UTF-8 character encoding universally
- Unicode preferred for single character encoding
- Ensures uniformity across systems
- No need to track/convert between encodings

## Facts and Claims

### Core Principles

- Avoid excessive claims about WordPress products/services
- Abide by proven facts
- Research when unsure
- Reach out for clarifications

### Guidelines

- **Don't speculate**: If fact isn't verified, don't include ambiguities
- **Don't predict**: Don't document or predict future WordPress features unless explicitly specified
- **Substantiate everything**: Facts must be proven before inclusion

### Verification Process

1. Check official WordPress sources
2. Consult WordPress Coding Standards
3. Verify with team members
4. Use authoritative external sources when needed

## Common Style Issues to Flag

### Critical

1. **Use of "we"**: Change to second person or passive
   - Wrong: "We recommend..."
   - Correct: "You can..." or "It is recommended..."

2. **Ableist language**: Flag immediately
   - Check for: crazy, insane, dumb, lame, blind to, crippled, etc.

3. **Non-inclusive terminology**:
   - Whitelist → Allowlist
   - Blacklist → Blocklist
   - Master → Main

4. **Gendered language**:
   - He/she → They
   - Guys → Everyone/folks/people

### Important

1. **Passive voice**: Change to active
   - Wrong: "The file is deleted by the function"
   - Correct: "The function deletes the file"

2. **Future tense**: Change to present
   - Wrong: "This will delete the file"
   - Correct: "This deletes the file"

3. **Cultural references**: Remove or replace
4. **Idioms and colloquialisms**: Replace with clear language
5. **Walls of text**: Break into smaller paragraphs
6. **Missing heading hierarchy**: Fix structure

### Suggestions

1. **Overly formal language**: Can be more conversational
2. **Long sentences**: Consider breaking up for clarity
3. **Lack of examples**: Suggest adding examples
4. **Missing visual aids**: Suggest images/diagrams where helpful

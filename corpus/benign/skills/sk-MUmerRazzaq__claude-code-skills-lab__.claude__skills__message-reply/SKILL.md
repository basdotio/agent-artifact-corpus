---
name: message-reply
description: Draft professional replies to received messages across platforms (LinkedIn, Fiverr, Upwork, Interview, Email, WhatsApp). This skill should be used when the user pastes a received message and needs a reply draft, or says "reply to this", "draft a response", "help me respond to".
---

# Message Reply Skill

Draft platform-appropriate professional replies with the user's authentic voice.

## Workflow

```
User pastes message → Identify platform → Apply platform rules → Generate reply + shorter alternative
```

## Required Context

| Input                | Description                                                 |
| -------------------- | ----------------------------------------------------------- |
| **received_message** | The message to reply to (user pastes it)                    |
| **platform**         | linkedin, fiverr, upwork, interview, email, whatsapp, other |

## Optional Context (Ask if relevant)

| Input             | When to Ask                                                            |
| ----------------- | ---------------------------------------------------------------------- |
| **your_context**  | If message mentions scheduling, availability, or specific situations   |
| **your_position** | If message asks about skills/experience user may want to clarify       |
| **action_intent** | If unclear whether to accept, decline, clarify, negotiate, or redirect |
| **tone**          | Only if user wants to override platform default                        |
| **length**        | Only if user wants to override (default: short)                        |

## Platform Detection

Auto-detect from message content or ask:

- "received this on linkedin" / "linkedin message" → LinkedIn
- "fiverr" / "gig" / "M Umer" (Fiverr name) → Fiverr
- "upwork" / "job" / "proposal" / "bid" → Upwork
- "interview" / "position" / "role" / "hiring" → Interview
- Formal greeting + business context → Email
- Casual / quick reply context → WhatsApp

## Platform Rules

See `references/platform-patterns.md` for detailed patterns. Quick reference:

| Platform  | Default Length | Default Tone        | Key Rule                             |
| --------- | -------------- | ------------------- | ------------------------------------ |
| LinkedIn  | 2-4 sentences  | Professional + warm | Acknowledge, stay connected          |
| Fiverr    | 2-3 sentences  | Friendly            | Redirect to project scope            |
| Upwork    | 4-6 sentences  | Natural/humanized   | Lead with solution approach          |
| Interview | 3-5 sentences  | Professional        | Honest about skills, include context |
| Email     | Structured     | Formal              | Clear sections, complete info        |
| WhatsApp  | 1-3 sentences  | Casual              | Quick, direct                        |

## Output Format

Always provide TWO versions (user frequently asks for shorter):

```markdown
## Reply

[Primary reply - platform appropriate]

## Shorter Alternative

[More concise version]

## Notes (if applicable)

- [Suggestions for additional context]
- [Warnings about message intent]
```

## Generation Rules

1. **Default SHORT** - User almost always asks for shorter. Start concise.
2. **No excessive emojis** - Max 1 emoji, only if platform-appropriate
3. **Honest positioning** - Never oversell skills. Phrase gaps as "learning" or "exploring"
4. **Redirect unclear requests** - If message is vague, ask what they need
5. **Include user context** - If user provides context (travel, schedule), weave it in naturally

## User Profile

See `references/user-profile.md` for skills, background, and common contexts.

Quick reference for honest positioning:

- **Strong**: n8n, Python, automation, AI agents, low-code/no-code, SDD/TDD
- **Learning**: React, Node.js (recently started)
- **Certified**: PIAIC Agentic AI Engineer

## Engineering Methodology (When Relevant)

User follows **Spec-Driven Development** and **Test-Driven Development**.

**Mention ONLY when client asks about:**

- Quality/reliability ("How do you ensure it works?")
- Process ("What's your development approach?")
- Documentation ("Will this be documented?")
- Past bad experiences ("Last freelancer's code broke")
- AI concerns ("Do you just use AI to generate code?")

**How to phrase in replies:**

If asked about process:

```
I follow spec-driven development — I document requirements first, write tests
before code, then implement. You get verified, documented code, not just
"it works on my machine."
```

If asked about AI usage:

```
Yes, I use AI tools like Claude Code, but I drive the architecture and verify
everything with tests. Specs and tests ensure the output is correct and reliable.
```

If asked about reliability:

```
I write tests first that define expected behavior. Code only ships when tests pass.
You also get specs and documentation in the repo.
```

**DON'T mention for:** Generic greetings, simple questions, casual chats.

## Common Scenarios

### Generic greeting (Fiverr/LinkedIn)

```
Input: "Hello M Umer, Good day, How are you today?"
Output: "Hi! I'm doing well, thank you. How can I help you today?"
```

### Skills question (Interview)

```
Input: "Are you experienced with n8n, Make, and Zapier?"
Context: Only n8n, self-learning
Output: "I have hands-on experience with n8n through personal projects. I haven't worked professionally with Make or Zapier yet, but I understand their concepts and can adapt quickly."
```

### Off-topic request (Fiverr)

```
Input: "Can you help with Facebook ads?"
Context: User does n8n automation, not ads
Output: "Thanks for reaching out! I specialize in n8n workflow automation and AI agents rather than Facebook ads. If you need any backend automation or API integrations, I'd be happy to help!"
```

### Availability question (Interview)

```
Input: "Are you available tomorrow for an interview?"
Context: Traveling to Lahore for class
Output: "Yes, I'll be traveling to Lahore tomorrow for my Agentic AI class. I'm available for an interview and can adjust timing. Please let me know what works best."
```

## Anti-Patterns

| Don't                              | Do Instead                                    |
| ---------------------------------- | --------------------------------------------- |
| Long paragraphs for simple replies | 2-4 sentences max for initial contact         |
| Oversell skills you're learning    | "Exploring" / "Recently started" / "Learning" |
| Generic "I can help with anything" | Specific: "I specialize in n8n and AI agents" |
| Multiple emojis                    | Max 1, or none for formal platforms           |
| Ignore user's additional context   | Weave travel/schedule/constraints naturally   |

## Checklist Before Output

- [ ] Platform identified and rules applied
- [ ] Length appropriate (default: short)
- [ ] Tone matches platform
- [ ] Honest about skills/experience
- [ ] User context included (if provided)
- [ ] Shorter alternative provided
- [ ] No overselling or excessive emojis

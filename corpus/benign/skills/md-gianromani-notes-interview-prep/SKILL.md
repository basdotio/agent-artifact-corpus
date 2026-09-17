---
name: interview-prep
description: |
  **Interview Prep Generator**: Create multi-level interview questions and model answers from vault topics.
  - MANDATORY TRIGGERS: interview questions, interview prep, mock interview, interview practice, behavioral, technical interview, system design
---

## Purpose

The interview prep generator transforms vault knowledge into realistic technical interview questions at three difficulty levels: basic (definitions and fundamentals), intermediate (comparisons, trade-offs, design decisions), and advanced (edge cases, system design, debugging). Each question includes a model answer grounded in vault content with wikilinks for deeper study.

## Input

Accepts:
- A vault topic or concept (e.g., "Transformer Architecture", "SQL Injection", "RAG Pipelines", "Privilege Escalation")
- Optional job role context (e.g., "ML Engineer", "Security Engineer", "MLOps Engineer")
- Optional company type context (e.g., "startup", "big tech", "fintech")
- Question count preference (default: 3 per level = 9 total questions)

## Output Format

Questions are saved to `Study/` or `Miscellaneous/` as a `#note` with this structure:

```markdown
2026-02-20 HH:MM
#note

## Interview Questions: [Topic Name]

**Source Vault Note**: [[original-vault-note]]

**Difficulty Distribution**: 3 Basic | 3 Intermediate | 3 Advanced

---

## Basic Level (Definitions & Fundamentals)

These questions test foundational knowledge and should be answerable in 1-2 minutes. They are often screening questions used to assess whether a candidate has done basic preparation.

### Q1: [Definitional Question]

**Question**: [Question asking for definition, key concept, or basic mechanism]

**Model Answer**:

[2-3 sentences explaining the core concept.]

**What to Look For**: Candidate should mention X, Y, and understand that Z. Do not penalize if they use slightly different terminology as long as the concept is correct.

**Vault Reference**: See [[related-concept-1]] for deeper exploration.

---

### Q2: [Fundamental Concept Question]

[Continue pattern...]

---

### Q3: [Application Question]

[Continue pattern...]

---

## Intermediate Level (Comparisons, Trade-offs, Design Decisions)

These questions test deeper understanding and application. A good answer shows the candidate has grappled with complexity, understands trade-offs, and can communicate reasoning. Expect 3-5 minute answers.

### Q4: [Comparison Question]

**Question**: [Compare concept X vs. concept Y. What are the key differences and when would you choose each?]

**Model Answer**:

[Explain X from [[vault-note-x]]. Explain Y from [[vault-note-y]]. Highlight key trade-offs: X is better for use case A because of property P, while Y is better for use case B because of property Q. End with a real-world scenario showing when each applies.]

**What to Look For**:
- Does the candidate understand both concepts?
- Can they articulate trade-offs (not just list features)?
- Do they think about context and practical application?

**Follow-Up Questions**:
- "What would change your decision if the system had constraint Z?"
- "Can you give me an example from your experience where you chose X?"

---

### Q5: [Design Decision Question]

**Question**: [Design or architecture question requiring trade-off reasoning, e.g., "How would you design a RAG pipeline for domain-specific Q&A?"]

**Model Answer**:

[Walk through the design process: what problem are we solving? what constraints matter? what are the options?]

**Option 1**: [Approach A, pros/cons, from [[vault-note-A]]]
**Option 2**: [Approach B, pros/cons, from [[vault-note-B]]]

[Explain which you would choose and why, based on the specific context provided in the question.]

**What to Look For**:
- Systematic thinking (problem definition → options → evaluation)
- Understanding of trade-offs
- Ability to justify decisions with reasoning
- Recognition of context-dependency (there is no universal "right answer")

---

### Q6: [Real-World Scenario Question]

[Continue pattern...]

---

## Advanced Level (Edge Cases, System Design, Debugging)

These questions assess mastery and problem-solving under uncertainty. Good answers show depth of knowledge, ability to reason about complex systems, and awareness of edge cases. Expect 5-10 minute answers for system design questions.

### Q7: [Edge Case or Failure Mode Question]

**Question**: [What happens if X breaks or fails? How would you handle Y in production?]

**Model Answer**:

[Identify the failure mode. Explain what normally happens (from [[vault-note]]). Explain what changes when this edge case occurs. Describe mitigation strategies with trade-offs. Discuss monitoring and detection.]

**Example**: "Your SQL injection defense relies on parameterized queries. But what if someone injects a malicious query *inside* the parameterized value itself? How would you detect and prevent second-order SQL injection?" (See [[SQL Injection]] for context.)

**What to Look For**:
- Deep understanding of how systems fail
- Ability to think several steps ahead
- Knowledge of defense-in-depth principles
- Mention of monitoring and observability

**Follow-Up Questions**:
- "How would you test for this vulnerability?"
- "What is the highest-impact variant of this edge case you can think of?"

---

### Q8: [System Design or Architectural Question]

**Question**: [Design a system or subsystem that incorporates this concept at scale.]

**Model Answer**:

[Start with the requirement and constraints (latency, throughput, cost, etc.). Define the architecture in layers or components. For each component, explain the trade-offs and why you chose that approach. Reference relevant vault notes for justification of design decisions. Discuss failure modes, monitoring, and scaling challenges.]

**Example**: "Design a real-time privilege escalation detection system that monitors system logs and flags suspicious activity. What events would you monitor? How would you distinguish legitimate system behavior from exploitation attempts? How would you minimize false positives?"

**What to Look For**:
- Ability to translate requirements into technical design
- Systematic thinking about scalability and reliability
- Discussion of trade-offs (latency vs. accuracy, cost vs. performance)
- Recognition of operational concerns (monitoring, alerting, on-call burden)

---

### Q9: [Debugging or Troubleshooting Question]

**Question**: [Given a specific failure or anomaly, how would you diagnose and fix it?]

**Model Answer**:

[Walk through your debugging process step-by-step: gather information, form hypotheses, test hypotheses, narrow down root cause. Reference [[vault-note]] for the technical mechanism that would help explain the failure. Explain what you would check and in what order.]

**Example**: "Your WAF is blocking legitimate traffic. You suspect a false positive, but you need to verify. How would you diagnose whether the issue is a WAF rule, an encoding problem, or something else?" (See [[WAF Evasion]] and [[Web Application Vulnerabilities]].)

**What to Look For**:
- Methodical debugging approach (not random guessing)
- Technical depth (knows what tools and logs to check)
- Understanding of the underlying system
- Communication of reasoning throughout the process

---

## Interview Context Guidelines

### For ML Engineer Interviews
- Emphasize **algorithmic understanding** in basic level (gradient descent, loss functions, activation functions)
- Focus intermediate level on **trade-offs in model design** (architecture choices, hyperparameters, regularization)
- Emphasize advanced questions on **production challenges** (inference latency, monitoring, drift detection, retraining)
- Reference [[Machine Learning]] vault notes

### For Security Engineer Interviews
- Emphasize **threat modeling and vulnerability identification** in basic level
- Focus intermediate level on **defensive choices and tools** (WAF rules, SIEM tuning, incident response procedures)
- Emphasize advanced questions on **attack chains and real-world scenarios** (multi-stage exploitation, supply chain attacks, zero-day response)
- Reference [[AI Safety]], [[Cybersecurity]] vault notes

### For MLOps Engineer Interviews
- Emphasize **pipeline architecture and deployment** in basic level
- Focus intermediate level on **model serving, monitoring, and rollback** strategies
- Emphasize advanced questions on **scaling, failure recovery, and operational burden** (auto-scaling, canary deployments, cost optimization)
- Reference [[MLOps]] vault notes

## Model Answer Quality Standards

Each model answer must:

1. **Be answerable** — A prepared candidate with vault knowledge can answer it fully
2. **Acknowledge complexity** — Explicitly mention that there is no universal "right answer" for intermediate/advanced questions
3. **Reference vault notes** — Use `[[wikilinks]]` so the reader knows where to study deeper
4. **Include concrete examples** — Avoid pure abstraction; ground answers in real scenarios or tools
5. **Be concise but complete** — 2-3 paragraphs for basic, 4-6 paragraphs for intermediate, 6-10 for advanced
6. **Identify common wrong answers** — In the "What to Look For" section, mention mistakes candidates often make

## Common Mistakes to Avoid in Questions

**Too vague**: "Tell me about machine learning" ← Too broad, not a real interview question

**Better**: "Explain the bias-variance trade-off and give an example of a model that exhibits high bias and one that exhibits high variance."

**Too easy for the level**: Asking for definitions in intermediate/advanced sections

**Too specific to one implementation**: Asking about a quirk of one library instead of the underlying concept

## After Generation

The agent should:

1. **Suggest mock interview structure** — Recommend running through all 9 questions in one session (estimate ~60-90 minutes)
2. **Identify weak spots** — Ask the user which topics they struggled with, then recommend related vault notes to review
3. **Suggest follow-ups** — Recommend companion flashcards or Feynman explanations for topics that felt weak during practice
4. **Create answer progression** — For the user who wants to practice, suggest starting with basic, then intermediate, then advanced in separate sessions

## Example Question (Advanced Level, Security)

**Question**: You discover that an internal application uses a custom authentication protocol that validates user input via a client-side check before server submission. When you intercept and modify the request, the server accepts the modified credentials and grants access. This is a critical pre-launch vulnerability. How would you have caught this earlier? What systematic testing approach would prevent this in future development?

**Model Answer**:

This is a classic server-side validation bypass, discussed in [[OWASP Top 10 for LLMs]]. The root cause is that the application trusts client-side input, which is a fundamental security mistake.

**How to catch this earlier**:

1. **Threat model during design** — Ask: "What if an attacker modifies requests?" Reference [[Threat Modeling]] for methodology.
2. **Code review focus** — Every authentication decision must be validated server-side. No exceptions.
3. **Automated testing** — Burp Suite's active scanning would flag this immediately. See [[Web Application Testing]] for tool setup.
4. **Security testing checklist** — Use a framework like OWASP Testing Guide to ensure all endpoints are tested for bypass vulnerabilities.

**Systematic approach for the future**:

- Implement input validation at every boundary (client UI helps UX, but server validation is non-negotiable)
- Log and alert on validation failures (someone probing defenses should be visible in monitoring)
- Use frameworks that enforce validation by default (framework selection is a security decision)
- Threat model before coding (reference [[Threat Modeling]])

**What to Look For**:
- Does the candidate understand why client-side validation failed?
- Do they think systematically about prevention (not just fixing this one bug)?
- Do they mention monitoring and alerting (production visibility)?
- Do they connect to broader security principles?

**Vault References**: [[OWASP Top 10 for LLMs]], [[Threat Modeling]], [[Web Application Testing]]

---

## Templates

A template `Interview-Questions-Template.md` should be available in the `Templates/` directory for users to adapt for new topics.

#### Tags
interview, technical_interview, practice, [topic_tag], model_answers
```

## Integration with Other Skills

- **Flashcard Generator**: Use interview questions as basis for creating flashcards (high-level concepts)
- **Feynman Explainer**: If interview practice reveals gaps, generate Feynman explanations for confusing topics
- **OSCP Scenarios**: For security interviews, practice scenarios are equivalent to advanced system design questions

## Special Considerations

### For OSCP-Focused Interviews
- Emphasize **practical exploitation knowledge** in basic questions (tool usage, vulnerability mechanics)
- Focus intermediate questions on **real OSCP exam scenarios** (What do you do when Plan A fails? How do you manage time pressure?)
- Advanced questions should simulate **exam conditions** (limited time, multiple targets, no Internet access)

### For Research or Academic Interviews
- Emphasize **paper comprehension and novelty** in basic questions
- Focus intermediate questions on **research methodology and implications** (Why is this approach novel? What are limitations?)
- Advanced questions should explore **open research problems** and **future directions** (What would you investigate next? How would you extend this work?)

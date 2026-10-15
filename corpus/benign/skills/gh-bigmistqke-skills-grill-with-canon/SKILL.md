---
name: grill-with-canon
description: Settle an open design question by interviewing the owner of the design, one question at a time, against the project's canon (CANON.md), and write each answer into the canon as it is settled. Use when the canon does not decide a choice, when two units of the canon contradict each other, when a word is vague or used two ways, when a new primitive or behaviour is being designed, or when the user wants to stress-test a plan or asks to be grilled. Works with the canon skill, which governs everything once the answers are written.
---

# Grill with canon

This skill settles a design question that the canon does not yet answer. It runs as an interview with the owner of the design, and it ends when every answer is a unit of the canon. The canon skill, beside this one, defines the units and governs the work that follows.

## 1. When to use it

1. The canon does not decide a choice you face, and the choice is not yours to make.
2. Two units of the canon contradict each other.
3. A word is vague, carries two meanings, or is used against its term.
4. Someone is designing a new primitive or behaviour, and the specs it resembles do not settle it.
5. The owner asks to stress-test a plan, or to be grilled.

## 2. Walk the decision tree

1. Read the units that cover the question before asking anything: the terms, the axioms and facts, and the specs nearby.
2. Lay out the decisions the question depends on. Settle a decision before the ones that depend on it.
3. Ask one question at a time. Give your recommended answer with each question, and say which units support it.
4. If the code or the canon can answer a question, read them instead of asking.
5. Keep asking until every branch of the tree has an answer. Do not stop at the first workable design.

## 3. Challenge every answer

1. Check the answer against the canon. If it contradicts a unit, name the conflict and the units at once, and ask which one holds.
2. Test the answer against concrete scenarios that probe its edges. Invent the scenarios yourself, and pick the ones most likely to break it.
3. When the owner says how something works, check the code. If the code disagrees, say so, with the file and the function.
4. When the owner uses a word against its term, name the conflict at once.
5. When a word is vague or carries two meanings, propose one precise term and ask the owner to choose.
6. When the answer follows from no axiom, an axiom is missing. Ask for the value behind the answer, and state it as an axiom.

## 4. Write as you go

1. Write each answer into the canon the moment it is settled. Do not collect answers for later.
2. Write each answer as the unit that fits it:
   - a term for a word;
   - an axiom for a value;
   - a fact for something the platform imposes;
   - a spec for a decision or a behaviour;
   - an exception for a fact that keeps a spec from holding fully.
3. When a word was used two ways, record the conflict and how it was settled in the body of its term. List the rejected words on the term's `_Avoid_:` line.
4. Write a decision record only for a choice that is hard to reverse, surprising without its context, and the result of a real trade-off.
5. Run `pnpm canon check` after each change to the canon, and keep it clean.

## 5. Hand back

1. End the session when every question has an answer written into the canon.
2. Summarise the units you added or changed, and any question the owner left open.
3. Hand the work to the canon skill: its procedures for changing code, adding behaviour and fixing defects take over from here.

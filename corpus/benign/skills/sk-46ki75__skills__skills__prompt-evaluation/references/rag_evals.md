# RAG Evaluation

When the prompt-under-test is part of a Retrieval-Augmented
Generation pipeline (the model is given retrieved context and must
answer faithfully), the standard rubric splits into **four
metrics** that together cover the pipeline end-to-end:

- **Faithfulness** — did the answer stay grounded in the context?
- **Answer Relevance** — did the answer actually address the
  question?
- **Context Precision** — did retrieval rank the relevant chunks
  high?
- **Context Recall** — did retrieval surface enough evidence to
  answer?

These four are the [RAGAs](https://docs.ragas.io/) standard. The
formulas are LLM-judge-compatible (most can be expressed as
counting claims supported by context vs. total claims) and have
been validated against human judgment.

## Whether you need this reference

Use this reference when the user's prompt:

- takes retrieved context as input (vector DB hits, doc snippets,
  search results) and produces an answer
- needs to be faithful to a source (vs. inventing facts)
- is the "answer" step of a larger RAG pipeline

If you're evaluating retrieval quality separately (e.g. "did the
right doc come back?"), the relevant metrics are context-precision
and context-recall. If you're evaluating the answer-generation
step in isolation, faithfulness and answer-relevance.

## The four metrics

### 1. Faithfulness

```text
Faithfulness = (claims in answer supported by context)
             / (total claims in answer)
```

**Three-step LLM procedure**:

1. Extract atomic factual claims from the answer.
2. For each claim, ask the judge whether the claim is supported
   by the retrieved context.
3. Return supported_count / total_count.

A pass threshold of 0.9 means at most 1 in 10 claims may go beyond
the context. Eugene Yan's industry benchmark: "typical factual
inconsistency/irrelevance rate is 5–10%, even after grounding...
prohibitively hard to go below 2%."

In promptfoo:

```yaml
assert:
  - type: context-faithfulness
    contextTransform: "output.context"     # extract context from response
    threshold: 0.9
```

`contextTransform` is a JS expression evaluated on the provider's
response to pull out the retrieved context (string or array of
strings).

Custom Python implementation (when you want to control the judge):

```python
import json
from anthropic import Anthropic
client = Anthropic()

EXTRACT_CLAIMS = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "claims": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["claims"],
        "additionalProperties": False,
    },
}

VERIFY = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "reasoning": {"type": "string"},
            "supported": {"type": "boolean"},
        },
        "required": ["reasoning", "supported"],
        "additionalProperties": False,
    },
}


def faithfulness(answer, context, model="claude-haiku-4-5-20251001"):
    # 1. Extract claims
    r = client.messages.create(
        model=model,
        max_tokens=600,
        temperature=0,
        messages=[{"role": "user", "content":
            f"Extract atomic factual claims from this answer.\n"
            f"<answer>{answer}</answer>"}],
        output_config={"format": EXTRACT_CLAIMS},
    )
    claims = json.loads(r.content[-1].text)["claims"]
    if not claims:
        return 1.0

    # 2. Verify each
    supported = 0
    for c in claims:
        r = client.messages.create(
            model=model,
            max_tokens=300,
            temperature=0,
            system=[{
                "type": "text",
                "text": "Decide whether the claim is supported by the context. "
                        "Reason briefly, then return a boolean.",
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content":
                f"<claim>{c}</claim>\n<context>{context}</context>"}],
            output_config={"format": VERIFY},
        )
        if json.loads(r.content[-1].text)["supported"]:
            supported += 1

    # 3. Ratio
    return supported / len(claims)
```

### 2. Answer Relevance

```text
Answer Relevance = mean_i cosine_sim(embed(generated_question_i),
                                     embed(original_question))
```

**Reverse-engineering procedure**: ask the judge to generate N
questions (typically 3) for which the answer would be a sensible
response. Measure embedding similarity between each generated
question and the user's original. Average.

The trick: if the answer is off-topic but well-grounded, the
generated questions will look unlike the user's question, and the
score drops.

In promptfoo:

```yaml
defaultTest:
  options:
    provider:
      text: anthropic:messages:claude-haiku-4-5-20251001
      embedding: openai:text-embedding-3-large
assert:
  - type: answer-relevance
    threshold: 0.7
```

(Anthropic does not currently offer an embeddings API, so the
embedding leg of `answer-relevance` requires an OpenAI or other
embedding provider.)

### 3. Context Precision

```text
Context Precision@K = Σ_k (Precision@k · relevance_k)
                    / |relevant chunks in top K|
```

For each rank position k, check if that chunk is relevant. Reward
ranking relevant chunks high. Punishes systems that put the right
chunk at rank 8 instead of rank 1.

In promptfoo:

```yaml
assert:
  - type: context-relevance
    contextTransform: "output.context"     # array of chunks
```

### 4. Context Recall

```text
Context Recall = (claims in reference supported by context)
               / (total claims in reference)
```

The mirror of faithfulness on the *reference answer* side: did
retrieval surface enough evidence to answer? Identifies the case
where the model failed because the retriever didn't return the
relevant chunk, not because the prompt is bad.

In promptfoo:

```yaml
assert:
  - type: context-recall
    value: "max purchase without approval is $500"
    threshold: 0.9
```

The `value` here is the reference (ground truth) answer.

## The quad together

The four metrics cover the pipeline end-to-end:

- **Recall** — did we retrieve enough?
- **Precision** — was retrieval well-ranked?
- **Faithfulness** — did we use the retrieval?
- **Answer Relevance** — did we answer the question?

A failing eval row breaks down by axis: low recall → retriever is
the bug; high recall but low faithfulness → answer-generation
prompt is the bug; high faithfulness but low answer-relevance →
the prompt is on-topic but going down a tangent.

## Quote-then-answer pattern (cheap faithfulness boost)

Anthropic's recommended hallucination mitigation for long-context
RAG: have the model **quote relevant passages first**, then answer
using only those quotes.

```text
You will be asked a question and given a set of documents.

First, in <quotes> tags, extract the exact passages from the
documents that are relevant to the question. If none of the
documents are relevant, write "NONE" in the <quotes> tags.

Then, in <answer> tags, answer the question using *only* the
quoted passages. If you wrote "NONE", say "I don't have enough
information to answer."

Question: {question}
<documents>{retrieved_context}</documents>
```

Why this helps:

- The model commits to a grounded view of the context before
  answering — reduces "hallucinate to fit the question."
- Quotes are regex-extractable, so you can grade them: "every
  claim in `<answer>` should be backed by something in `<quotes>`."
- The "NONE → I don't know" escape hatch is itself an anti-
  hallucination lever.

## Additional anti-hallucination patterns

From Anthropic's [Reduce hallucinations](https://platform.claude.com/docs/en/docs/test-and-evaluate/strengthen-guardrails/reduce-hallucinations):

- **Allow Claude to say "I don't know"** — explicit permission to
  refuse rather than confabulate.
- **External knowledge restriction** — "Use only information from
  provided documents and not your general knowledge."
- **Verify with citations** — "For each claim, find a direct quote
  that supports it. If you can't find a supporting quote, remove
  the claim."
- **Best-of-N consistency check** — run the same prompt N times;
  inconsistencies across outputs flag likely hallucinations.

Each of these maps cleanly to an eval pattern:

- The "I don't know" lever: classification eval — pass if the
  output refuses on the no-evidence rows.
- External knowledge restriction: faithfulness eval as above.
- Citation verification: regex extraction of `<quotes>` + LLM
  judge on each claim.
- Best-of-N: code-graded consistency check (e.g. set match across
  samples, or pairwise judge agreement).

## Production realism

Eugene Yan's industry calibration: "typical factual
inconsistency/irrelevance rate is 5–10%, even after grounding...
and from what I've learned from LLM providers, it may be
prohibitively hard to go below 2%."

Set thresholds against this floor:

- 0.95 = near-state-of-the-art; expect 1 in 20 fails
- 0.90 = solid production
- 0.85 = needs work
- < 0.80 = the prompt or the retriever is broken

For a pre-deploy gate, 0.90 on faithfulness AND 0.85 on
answer-relevance is a defensible default.

## Source citations

- [RAGAs — Faithfulness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)
- [RAGAs — Answer Relevancy](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_relevance/)
- [RAGAs — Context Precision](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/)
- [RAGAs — Context Recall](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/)
- [promptfoo — answer-relevance](https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/answer-relevance)
- [promptfoo — context-faithfulness](https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/context-faithfulness)
- [Anthropic — Reduce hallucinations](https://platform.claude.com/docs/en/docs/test-and-evaluate/strengthen-guardrails/reduce-hallucinations)
- [Eugene Yan — Task-Specific LLM Evals](https://eugeneyan.com/writing/evals/)

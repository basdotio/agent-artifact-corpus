"""Small, dependency-free contract shared by a Laya client and its adapter.

Both sides may import this module: the client (``laya.py``) rejects bad input before a network
round trip, while an adapter can use ``check_token_budget`` after loading the actual tokenizer.
"""

import json
import math
import re

PROTOCOL = "laya.decision.v1"

# Cheap pre-flight limits. The adapter still enforces the real token budget; these stop an agent
# from sending something that Laya would silently cut mid-question, and give it a fixable error.
MAX_QUESTION_ID = 64
MAX_INSTRUCTIONS_CHARS = 600
MAX_OPTION_LABEL_CHARS = 64
MAX_OPTION_TEXT_CHARS = 240
MAX_STATE_CHARS = 24000
MAX_PAYLOAD_CHARS = 32000


class DecisionError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def require(condition, message, code="invalid_input"):
    if not condition:
        raise DecisionError(code, message)


def validate_request(payload):
    require(isinstance(payload, dict), "Input must be a JSON object.")
    require(set(payload) == {"state", "questions"}, "Expected state and questions only.")
    require(isinstance(payload["state"], (str, dict, list)), "State must be text, object or array.")
    questions = payload["questions"]
    require(isinstance(questions, dict) and 1 <= len(questions) <= 32, "Use 1–32 questions per request.")
    for qid, q in questions.items():
        require(isinstance(qid, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", qid), "Use short ASCII question IDs.")
        require(isinstance(q, dict) and set(q) <= {"type", "instructions", "criteria"}, "Invalid question fields.")
        require(q.get("type") in ("choice", "score", "noul"), "Unsupported question type.")
        require(isinstance(q.get("instructions"), str) and q["instructions"].strip(), "Write explicit string instructions.")
        require(len(q["instructions"]) <= MAX_INSTRUCTIONS_CHARS, "Shorten question instructions to 600 characters.")
        crit = q.get("criteria")
        if q["type"] == "choice":
            require(isinstance(crit, dict) and 2 <= len(crit) <= 20, "Shortlist to 2–20 Choice options.")
            require(all(isinstance(k, str) and k and (v is None or isinstance(v, str)) for k, v in crit.items()), "Choice criteria must map names to strings or null.")
            require(all(len(k) <= MAX_OPTION_LABEL_CHARS for k in crit), "Shorten Choice option names to 64 characters.")
            require(all(v is None or len(v) <= MAX_OPTION_TEXT_CHARS for v in crit.values()), "Shorten each Choice criterion to 240 characters; Laya clips long option text and the labels stop being distinguishable.")
        elif q["type"] == "score":
            require(isinstance(crit, list) and 2 <= len(crit) <= 10 and all(isinstance(v, str) and v for v in crit), "Score needs 2–10 described, ordered levels.")
            require(all(len(v) <= MAX_OPTION_TEXT_CHARS for v in crit), "Shorten each Score level description to 240 characters.")
        else:
            require(crit is None or (isinstance(crit, dict) and set(crit) <= {"true", "false"} and all(isinstance(v, str) and len(v) <= MAX_OPTION_TEXT_CHARS for v in crit.values())), "Noul criteria may describe true and false in at most 240 characters each.")
    require(len(payload["questions"]) <= 32, "Use at most 32 questions per request.")
    state_chars = len(payload["state"]) if isinstance(payload["state"], str) else len(json.dumps(payload["state"], ensure_ascii=False, default=str))
    require(state_chars <= MAX_STATE_CHARS, "Shorten the state to 24000 characters; Laya would truncate it and the answer would describe the cut text.", "context_budget_exceeded")
    try:
        json.dumps(payload, allow_nan=False)
    except (ValueError, TypeError):
        raise DecisionError("invalid_input", "Input must be finite JSON data.") from None
    require(len(json.dumps(payload, ensure_ascii=False, default=str)) <= MAX_PAYLOAD_CHARS, "Send less evidence per request: split the questions or shorten the state.", "context_budget_exceeded")
    return payload


def validate_answers(answers, questions):
    require(isinstance(answers, dict) and set(answers) == set(questions), "Response question IDs differ from the request.", "invalid_response")

    def number(value, lo=0, hi=1):
        require(type(value) in (int, float) and math.isfinite(value) and lo <= value <= hi, "Response contains an invalid numeric value.", "invalid_response")

    for qid, q in questions.items():
        answer = answers[qid]
        require(isinstance(answer, dict) and answer.get("type") == q["type"], "Response answer type differs from the request.", "invalid_response")
        if "confidence" in answer:
            number(answer["confidence"])
        if "action" in answer:
            require(isinstance(answer["action"], dict), "Invalid action metadata.", "invalid_response")
            if "act_probability" in answer["action"]:
                number(answer["action"]["act_probability"])
        if q["type"] == "noul":
            number(answer.get("noul"))
            continue
        number(answer.get("confidence"))
        expected = set(q["criteria"]) if q["type"] == "choice" else {str(i) for i in range(len(q["criteria"]))}
        probs = answer.get("probabilities")
        require(isinstance(probs, dict) and set(probs) == expected, "Response options differ from the request.", "invalid_response")
        for value in probs.values():
            number(value)
        require(abs(sum(probs.values()) - 1) <= 0.003, "Probabilities do not sum to one.", "invalid_response")
        if q["type"] == "choice":
            chosen = answer.get("choice")
            require(isinstance(chosen, str) and chosen in expected, "Response selected an unknown option.", "invalid_response")
            require(probs[chosen] >= max(probs.values()) - 0.0001, "Choice disagrees with its probabilities.", "invalid_response")
        else:
            number(answer.get("score"), 0, len(expected) - 1)
            require(answer.get("legend") == {str(i): v for i, v in enumerate(q["criteria"])}, "Score legend differs from the rubric.", "invalid_response")
            mean = sum(int(k) * v for k, v in probs.items())
            require(abs(answer["score"] - mean) <= 0.01, "Score disagrees with its distribution.", "invalid_response")
    return answers


def check_token_budget(agent, payload):
    """Adapter-side guard: reject truncation on the dynamic path; mirrors Laya 0.3.5 formatting.

    The adapter or local runtime calls this with a real Laya ``Agent`` and tokenizer. The generic
    client does not call it; it uses the character limits in ``validate_request`` instead.
    """
    tok = agent.tok
    max_len = agent.cfg.get("max_len", 512)
    head_limit = agent.cfg.get("head_max_len", 192)

    def tokens(text):
        return len(tok(text.replace(tok.mask_token, " "), add_special_tokens=False)["input_ids"])

    state = payload["state"]
    state_tokens = tokens(state if isinstance(state, str) else json.dumps(state, ensure_ascii=False))
    for q in payload["questions"].values():
        crit = q.get("criteria")
        if q["type"] == "choice":
            options = [k if v in (None, "") else f"{k}: {v}" for k, v in crit.items()]
        elif q["type"] == "score":
            options = [f"level {i}: {v}" for i, v in enumerate(crit)]
        else:
            crit = crit or {}
            options = ["false: " + (crit.get("false") or "no, the statement does not hold"), "true: " + (crit.get("true") or "yes, the statement holds")]
        lengths = [tokens(" " + option) for option in options]
        require(max(lengths) <= 48, "Shorten each criterion: Laya clips option text after 48 tokens.", "context_budget_exceeded")
        option_tokens = sum(length + 1 for length in lengths)
        instruction_tokens = tokens(q["type"] + " question: " + q["instructions"])
        require(head_limit - option_tokens >= max(16, instruction_tokens), "Shorten the instructions/options or reduce the shortlist; the question head would be truncated.", "context_budget_exceeded")
        require(instruction_tokens + option_tokens + state_tokens + 4 <= max_len, "Shorten or split the evidence; state would be truncated. Nothing was inferred.", "context_budget_exceeded")
    return {"max_len": max_len, "head_max_len": head_limit, "state_tokens": state_tokens, "input_truncated": False}

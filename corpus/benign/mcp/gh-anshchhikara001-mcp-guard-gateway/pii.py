"""Finds Indian PII in text, using Presidio with a medium-sized spaCy model."""

from dataclasses import dataclass

from presidio_analyzer import (
    AnalyzerEngine,
    EntityRecognizer,
    Pattern,
    PatternRecognizer,
    RecognizerRegistry,
)
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import (
    InAadhaarRecognizer,
    InGstinRecognizer,
    InPanRecognizer,
    InPassportRecognizer,
    InVehicleRegistrationRecognizer,
    InVoterRecognizer,
)

# The Indian identifiers are found by patterns; the model matters for person names, which
# Pseudonyms need. On sentences with Indian names the medium model (about 40 MB) found the full
# name 85% of the time against 73% for the small one. Presidio's default large model needs
# about 600 MB more memory.
SPACY_MODEL = "en_core_web_md"

# Presidio scores each match from 0 to 1. Weak patterns (any 10 characters with 4 digits could be
# a PAN) score near 0 and reach 0.4 only when a context word such as "PAN" is nearby, so 0.4
# keeps a weak match only when the text backs it up.
SCORE_THRESHOLD = 0.4


def _pattern_recognizer(
    entity_type: str, patterns: list[tuple[str, float]], context: list[str]
) -> PatternRecognizer:
    """A recognizer from (regex, score) pairs; nearby context words raise the score."""
    return PatternRecognizer(
        supported_entity=entity_type,
        name=f"{entity_type}_recognizer",
        patterns=[Pattern(entity_type, regex, score) for regex, score in patterns],
        context=context,
    )


def _recognizers() -> list[EntityRecognizer]:
    """Presidio's own Indian recognizers, plus ours for identifiers Presidio doesn't know."""
    return [
        InAadhaarRecognizer(),  # validates the Verhoeff check digit
        InPanRecognizer(),
        InGstinRecognizer(),
        InPassportRecognizer(),
        InVoterRecognizer(),
        InVehicleRegistrationRecognizer(),
        # A UPI ID is a handle, "@" and a bank's or app's name: "priya.k92@okaxis". Unlike an
        # email address there is no dot after the name, which is how the two are told apart.
        _pattern_recognizer(
            "IN_UPI_ID",
            [(r"(?<![\w.-])[a-z0-9][\w.-]{1,255}@[a-z][a-z0-9]{1,63}(?![\w-]|\.[a-z0-9])", 0.6)],
            ["upi", "vpa"],
        ),
        # An IFSC is a bank code of 4 letters, a zero, then 6 letters or digits for the branch.
        # Order or product codes can have that shape too ("ORDR0012345"), and an IFSC is a public
        # branch code rather than a Customer's own, so it counts only next to a word like "IFSC".
        _pattern_recognizer(
            "IN_IFSC",
            [(r"\b[a-z]{4}0[a-z0-9]{6}\b", 0.1)],
            ["ifsc", "branch", "neft", "rtgs", "imps"],
        ),
        # An Indian mobile number has 10 digits starting with 6-9, optionally after +91 or 0,
        # often split 5 + 5, sometimes with the first 5 in brackets. Digits glued to "-" or "#"
        # are part of an ID ("ORD-9820145763"). Landlines aren't covered. Bare 10 digits count
        # as a phone even with no word like "phone" nearby, since missing a Customer's phone
        # leaks it while a wrong Pseudonym is harmless, but score just low enough that an account
        # number backed by a word like "account" wins where the two overlap.
        _pattern_recognizer(
            "IN_PHONE",
            [
                (r"(?<![\w+#-])(?:\+91|0091)[\s-]?[6-9]\d{4}[\s-]?\d{5}\b", 0.7),
                (r"(?<![\w+#-])(?:0?[6-9]\d{4}|\(0?[6-9]\d{4}\))[\s-]?\d{5}\b", 0.4),
            ],
            ["phone", "mobile", "call", "contact", "whatsapp", "sms", "otp"],
        ),
        # A bank account number is 9 to 18 digits, which on its own could be almost any number,
        # so it counts only next to a word like "account". spaCy splits "a/c" into three words,
        # too short to use as context, so the second pattern looks for it right before the digits
        # (Python's lookbehinds must be fixed width, hence one per spelling). Twelve digits that
        # pass the Aadhaar check are found as an Aadhaar instead, which scores higher.
        _pattern_recognizer(
            "IN_BANK_ACCOUNT",
            [
                (r"\b\d{9,18}\b", 0.1),
                (
                    r"(?:(?<=a/c )|(?<=a/c: )|(?<=a/c no )|(?<=a/c no\. )|(?<=a/c no: ))"
                    r"\d{9,18}\b",
                    0.5,
                ),
            ],
            ["account", "acct", "beneficiary"],
        ),
    ]


# Every entity type the detector finds.
ENTITY_TYPES: tuple[str, ...] = tuple(
    entity_type for recognizer in _recognizers() for entity_type in recognizer.supported_entities
)


@dataclass(frozen=True)
class PiiMatch:
    entity_type: str
    start: int
    end: int
    text: str
    score: float


class PiiDetector:
    def __init__(self) -> None:
        nlp_engine = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": SPACY_MODEL}],
            }
        ).create_engine()
        registry = RecognizerRegistry(supported_languages=["en"])
        for recognizer in _recognizers():
            registry.add_recognizer(recognizer)
        self._analyzer = AnalyzerEngine(
            registry=registry, nlp_engine=nlp_engine, supported_languages=["en"]
        )

    def find(self, text: str) -> list[PiiMatch]:
        """Every piece of PII in the text, in the order it appears.

        Where matches overlap (ten digits can be a phone and an account number), only the one
        with the highest score is kept, so each piece of text has one entity type.
        """
        results = self._analyzer.analyze(
            text=text,
            language="en",
            entities=list(ENTITY_TYPES),
            score_threshold=SCORE_THRESHOLD,
        )
        kept: list[PiiMatch] = []
        for result in sorted(
            results, key=lambda result: (-result.score, result.start - result.end)
        ):
            if all(result.end <= match.start or match.end <= result.start for match in kept):
                kept.append(
                    PiiMatch(
                        result.entity_type,
                        result.start,
                        result.end,
                        text[result.start : result.end],
                        result.score,
                    )
                )
        return sorted(kept, key=lambda match: match.start)

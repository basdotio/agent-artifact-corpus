import pytest

from app.bedrock import extract_json_object
from app.schemas import SchemaValidationError, VerdictResponse


def test_decisive_verdict_requires_citation():
    with pytest.raises(SchemaValidationError):
        VerdictResponse.model_validate(
            {
                "verdict": "SUPPORTED",
                "confidence": 0.8,
                "reasoning": "The retrieved source confirms the claim.",
                "citations": [],
            }
        )


def test_unverified_can_have_no_citations():
    verdict = VerdictResponse.model_validate(
        {
            "verdict": "UNVERIFIED",
            "confidence": 0.0,
            "reasoning": "No verified source clearly addressed the claim.",
            "citations": [],
        }
    )

    assert verdict.verdict == "UNVERIFIED"


def test_extract_json_object_handles_markdown_wrapped_output():
    assert extract_json_object('```json\n{"verdict":"UNVERIFIED"}\n```') == (
        '{"verdict":"UNVERIFIED"}'
    )

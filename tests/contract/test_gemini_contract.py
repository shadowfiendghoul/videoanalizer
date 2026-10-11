"""Contract tests validating Gemini API JSON structure against schema."""

import json
from pathlib import Path

from videoanalizer.services.analyzer import AnalysisResponseSchema


def test_gemini_mock_fixture_conforms_to_schema() -> None:
    """Verify that tests/fixtures/gemini_responses/humor_analysis.json validates against AnalysisResponseSchema."""
    fixture_path = Path("tests/fixtures/gemini_responses/humor_analysis.json")
    data = json.loads(fixture_path.read_text(encoding="utf-8"))

    validated = AnalysisResponseSchema.model_validate(data)
    assert len(validated.highlights) >= 1

    for h in validated.highlights:
        assert 0.0 <= h.humor_score <= 10.0
        assert h.start_sec < h.end_sec
        assert len(h.suggested_headline) > 0
        assert len(h.word_timings) > 0
        for w in h.word_timings:
            assert w.start_sec <= w.end_sec

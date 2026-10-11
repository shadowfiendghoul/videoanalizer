"""Unit tests for AnalyzerService parsing and error handling."""

from collections.abc import AsyncGenerator
from pathlib import Path
from types import TracebackType
from unittest.mock import MagicMock, patch

from videoanalizer.config import AppConfig
from videoanalizer.models.source_video import SourceVideo
from videoanalizer.services.analyzer import AnalyzerService


def test_analyzer_parses_mock_json_successfully(
    mock_source_video: SourceVideo,
    sample_config: AppConfig,
) -> None:
    """Test AnalyzerService correctly converts structured Gemini JSON into HighlightSegments."""
    fixture_path = Path("tests/fixtures/gemini_responses/humor_analysis.json")
    mock_json = fixture_path.read_text(encoding="utf-8")

    service = AnalyzerService()

    # Mock google-genai Client and upload
    mock_client = MagicMock()
    mock_file = MagicMock()
    mock_file.name = "files/test_file_123"
    mock_file.state = "ACTIVE"
    mock_client.files.upload.return_value = mock_file
    mock_client.files.get.return_value = mock_file

    mock_response = MagicMock()
    mock_response.text = mock_json
    mock_client.models.generate_content.return_value = mock_response

    with patch("videoanalizer.services.analyzer.genai.Client", return_value=mock_client):
        highlights = service.analyze(
            video=mock_source_video,
            clip_count=2,
            min_duration=30.0,
            max_duration=60.0,
            config=sample_config,
        )

    assert len(highlights) == 2
    # Sorted by humor score descending (9.2 then 8.7)
    assert highlights[0].humor_score == 9.2
    assert highlights[1].humor_score == 8.7
    assert len(highlights[0].word_timings) == 5
    assert "elevator" in highlights[0].suggested_headline.lower()


def test_analyzer_live_api_success(
    mock_source_video: SourceVideo,
) -> None:
    """Test AnalyzerService routes to Live API and parses tool call highlights."""
    live_config = AppConfig(
        GOOGLE_API_KEY="test_gemini_api_key_mock_12345",
        GEMINI_MODEL="gemini-2.5-flash-native-audio-latest",
        OUTPUT_DIR=Path("./test_output"),
    )
    service = AnalyzerService()

    # Mock tool call response
    mock_func_call = MagicMock()
    mock_func_call.name = "report_funny_moments"
    mock_func_call.args = {
        "highlights": [
            {
                "start_sec": 10.0,
                "end_sec": 25.0,
                "humor_score": 9.5,
                "summary": "Hilarious joke about coding",
                "suggested_headline": "WHEN THE CODE ACTUALLY COMPILES 😂",
                "transcript": "Wait it worked on the first try",
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.tool_call.function_calls = [mock_func_call]
    mock_response.server_content = None

    class MockAsyncSession:
        async def __aenter__(self) -> "MockAsyncSession":
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
        ) -> None:
            return None

        async def send(self, *args: object, **kwargs: object) -> None:
            pass

        async def receive(self) -> AsyncGenerator[object, None]:
            yield mock_response

    mock_client = MagicMock()
    mock_client.aio.live.connect.return_value = MockAsyncSession()

    with (
        patch("videoanalizer.services.analyzer.genai.Client", return_value=mock_client),
        patch.object(service, "_extract_pcm_16k", return_value=b"\x00" * 64000),
    ):
        highlights = service.analyze(
            video=mock_source_video,
            clip_count=1,
            min_duration=10.0,
            max_duration=30.0,
            config=live_config,
        )

    assert len(highlights) == 1
    assert highlights[0].humor_score == 9.5
    assert highlights[0].start_sec == 10.0
    assert highlights[0].end_sec == 25.0
    assert "WHEN THE CODE" in highlights[0].suggested_headline
    assert len(highlights[0].word_timings) > 0

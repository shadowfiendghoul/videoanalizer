"""Unit tests for silence detection and segment padding calculation."""

from videoanalizer.models.render_job import SilenceConfig
from videoanalizer.services.silence import SilenceDetector


def test_compute_keep_segments_no_silences() -> None:
    """Test when no silences are found, full clip is retained."""
    detector = SilenceDetector()
    segments = detector.compute_keep_segments(duration=30.0, silences=[])
    assert segments == [(0.0, 30.0)]


def test_compute_keep_segments_with_padding() -> None:
    """Test that speech boundaries are padded when cutting silence."""
    detector = SilenceDetector()
    # A 5-second silence in the middle (10s to 15s) of a 30s clip
    silences = [(10.0, 15.0)]
    # With 100ms padding, silence shrinks to (10.1, 14.9)
    # Speech to keep is (0 to 10.1) and (14.9 to 30.0)
    segments = detector.compute_keep_segments(duration=30.0, silences=silences, padding_ms=100)

    assert len(segments) == 2
    assert segments[0][0] == 0.0
    assert segments[0][1] >= 10.05
    assert segments[1][0] <= 14.95
    assert segments[1][1] == 30.0


def test_compute_keep_segments_short_silence_absorbed() -> None:
    """Test that a silence shorter than 2x padding gets absorbed."""
    detector = SilenceDetector()
    # 150ms silence with 100ms padding (200ms total padding)
    silences = [(10.0, 10.15)]
    segments = detector.compute_keep_segments(duration=20.0, silences=silences, padding_ms=100)
    # Silence is absorbed because padding exceeds gap
    assert segments == [(0.0, 20.0)]

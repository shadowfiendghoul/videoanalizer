"""Transcription timing management and word-level synchronization service."""

from videoanalizer.models.highlight import HighlightSegment, WordTiming


class TranscriptionService:
    """Service providing word timings for karaoke subtitles with fallback estimation."""

    def get_word_timings(self, highlight: HighlightSegment) -> list[WordTiming]:
        """Retrieve word-level timestamps from highlight, falling back to estimation if empty."""
        if highlight.word_timings:
            return highlight.word_timings

        return self.estimate_word_timings(highlight.transcript, highlight.duration_sec)

    def estimate_word_timings(self, transcript: str, duration: float) -> list[WordTiming]:
        """Proportionally space words across duration when per-word timing is absent.

        Args:
            transcript: Full dialogue text.
            duration: Segment duration in seconds.

        Returns:
            List of estimated WordTiming objects.
        """
        words = transcript.strip().split()
        if not words or duration <= 0:
            return []

        # Leave small margins at beginning and end
        usable_duration = max(0.2, duration - 0.4)
        word_slot = usable_duration / len(words)

        results: list[WordTiming] = []
        current_time = 0.2

        for w in words:
            end_time = min(duration, current_time + (word_slot * 0.9))
            results.append(
                WordTiming(
                    word=w,
                    start_sec=round(current_time, 2),
                    end_sec=round(max(current_time + 0.05, end_time), 2),
                )
            )
            current_time += word_slot

        return results

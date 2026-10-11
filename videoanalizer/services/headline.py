"""AI hook headline generation and re-prompting service."""

import contextlib
import logging

from google import genai

from videoanalizer.config import AppConfig
from videoanalizer.models.highlight import HighlightSegment

logger = logging.getLogger(__name__)


class HeadlineService:
    """Service managing viral TikTok hook headline suggestions."""

    def get_headline(self, highlight: HighlightSegment) -> str:
        """Return the AI headline already associated with the highlight."""
        return highlight.suggested_headline or "WATCH TILL THE END 💀😂"

    def regenerate_headline(self, highlight: HighlightSegment, config: AppConfig) -> str:
        """Request a fresh viral hook headline from Gemini for the selected comedic highlight."""
        client = genai.Client(api_key=config.google_api_key.get_secret_value())

        prompt = (
            "Generate a single short, punchy, viral TikTok hook headline "
            "(under 70 characters with emojis) for this funny moment:\n\n"
            f"Moment: {highlight.summary}\n"
            f"Dialogue: {highlight.transcript}\n\n"
            "Output ONLY the headline text, nothing else."
        )

        target_model = config.gemini_model
        if "native-audio" in target_model.lower() or "live" in target_model.lower():
            target_model = "gemini-3.8-flash"

        with contextlib.suppress(Exception):
            response = client.models.generate_content(
                model=target_model,
                contents=prompt,
            )
            headline = response.text.strip().strip('"').strip("'")
            if headline:
                highlight.suggested_headline = headline[:100]
                return highlight.suggested_headline

        return self.get_headline(highlight)

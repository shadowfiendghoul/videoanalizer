"""Multimodal AI humor detection and transcription service supporting both REST and Live API."""

import asyncio
import contextlib
import json
import logging
import subprocess
import time
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from videoanalizer.config import AppConfig
from videoanalizer.exceptions import (
    AnalysisError,
    AnalysisTimeoutError,
    ContentFilteredError,
    RateLimitError,
    SchemaValidationError,
)
from videoanalizer.models.highlight import HighlightSegment, WordTiming
from videoanalizer.models.source_video import SourceVideo
from videoanalizer.services.transcriber import TranscriptionService
from videoanalizer.utils.ffmpeg_check import ensure_ffmpeg

logger = logging.getLogger(__name__)


class RawWordTiming(BaseModel):
    """Raw schema for word timing from Gemini."""

    word: str
    start_sec: float
    end_sec: float


class RawHighlight(BaseModel):
    """Raw schema for single highlight segment from Gemini."""

    start_sec: float
    end_sec: float
    humor_score: float = Field(ge=0.0, le=10.0)
    summary: str
    transcript: str = ""
    word_timings: list[RawWordTiming] = Field(default_factory=list)
    suggested_headline: str


class AnalysisResponseSchema(BaseModel):
    """Top-level structured JSON schema requested from Gemini in REST mode."""

    highlights: list[RawHighlight]
    video_language: str = "en"
    analysis_notes: str = ""


# Live API Function Declaration for Tool Calling
REPORT_FUNNY_MOMENTS_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="report_funny_moments",
            description="Report detected funny moments from video audio dialogue.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "highlights": types.Schema(
                        type="ARRAY",
                        items=types.Schema(
                            type="OBJECT",
                            properties={
                                "start_sec": types.Schema(type="NUMBER"),
                                "end_sec": types.Schema(type="NUMBER"),
                                "humor_score": types.Schema(type="NUMBER"),
                                "summary": types.Schema(type="STRING"),
                                "transcript": types.Schema(type="STRING"),
                                "suggested_headline": types.Schema(type="STRING"),
                            },
                            required=[
                                "start_sec",
                                "end_sec",
                                "humor_score",
                                "summary",
                                "suggested_headline",
                            ],
                        ),
                    )
                },
                required=["highlights"],
            ),
        )
    ]
)


class AnalyzerService:
    """Service orchestrating video humor detection via Gemini REST or Live API."""

    SYSTEM_PROMPT_TEMPLATE = (
        "You are an expert comedy editor and viral video producer.\n"
        "Analyze this video/audio for the funniest, most entertaining moments.\n\n"
        "Video Context:\n"
        "Total video duration is {duration:.1f} seconds. All timestamps MUST be within [0.0, {duration:.1f}].\n\n"
        "Task:\n"
        "Find and return EXACTLY {clip_count} highlight moments, "
        "each between {min_duration} and {max_duration} seconds long.\n\n"
        "For each highlight segment:\n"
        "1. 'start_sec': Start timestamp in seconds (decimal, e.g. 42.5). Must be < {duration:.1f}.\n"
        "2. 'end_sec': End timestamp in seconds (decimal, e.g. 78.2). Must be <= {duration:.1f} and > start_sec.\n"
        "3. 'humor_score': Rating from 0.0 to 10.0 based on comedy value.\n"
        "4. 'summary': Brief description (under 200 chars) explaining why it's funny.\n"
        "5. 'transcript': Full dialogue transcript for this segment.\n"
        "6. 'word_timings': List of words with 'word', 'start_sec', 'end_sec'.\n"
        "7. 'suggested_headline': A short viral TikTok hook headline (under 100 chars).\n\n"
        "Prioritize moments with clear punchlines, laughs, and high comedic energy.\n"
        "Respond strictly in valid JSON matching the schema."
    )

    def __init__(self) -> None:
        self.transcriber = TranscriptionService()

    def _extract_audio_if_large(
        self, video_path: Path, max_size_bytes: int = 100 * 1024 * 1024
    ) -> Path:
        """Extract audio if video exceeds size threshold for REST upload."""
        if video_path.stat().st_size <= max_size_bytes:
            return video_path

        audio_output = video_path.parent / f"{video_path.stem}_audio.m4a"
        if audio_output.exists() and audio_output.stat().st_size > 0:
            return audio_output

        ensure_ffmpeg()
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(audio_output),
        ]
        try:
            subprocess.run(cmd, capture_output=True, check=True)  # noqa: S603
            return audio_output
        except Exception as exc:
            logger.warning(
                "Audio extraction failed (%s), falling back to raw video: %s", video_path, exc
            )
            return video_path

    def _extract_pcm_16k(self, video_path: Path) -> bytes:
        """Extract 16kHz mono 16-bit PCM audio stream for Live API."""
        ensure_ffmpeg()
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-f",
            "s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-",
        ]
        proc = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            check=True,
        )
        return proc.stdout

    def _parse_raw_highlights(
        self,
        raw_items: list[dict],
        video: SourceVideo,
        min_duration: float,
    ) -> list[HighlightSegment]:
        """Convert raw highlight dicts into validated HighlightSegment domain models."""
        results: list[HighlightSegment] = []
        for raw in raw_items:
            start = max(0.0, float(raw.get("start_sec", 0.0)))
            end = float(raw.get("end_sec", start + min_duration))

            # Auto-normalize if model returned milliseconds or deciseconds
            if start > video.duration_sec:
                if start / 1000.0 < video.duration_sec:
                    start /= 1000.0
                    end /= 1000.0
                elif start / 10.0 < video.duration_sec:
                    start /= 10.0
                    end /= 10.0

            # Discard segments starting beyond video duration
            if start >= video.duration_sec - 1.0:
                logger.warning(
                    "Skipping highlight starting at %.1fs beyond video duration %.1fs",
                    start,
                    video.duration_sec,
                )
                continue

            if end <= start:
                end = start + min_duration
            elif (end - start) < min_duration:
                end = min(video.duration_sec, start + min_duration)

            if end > video.duration_sec:
                end = video.duration_sec

            if end <= start:
                continue

            transcript = str(raw.get("transcript", "")).strip()
            word_timings_raw = raw.get("word_timings", [])
            words: list[WordTiming] = []

            if word_timings_raw:
                for w in word_timings_raw:
                    w_word = str(w.get("word", "")).strip()
                    if w_word:
                        w_start = max(start, float(w.get("start_sec", start)))
                        w_end = max(w_start + 0.05, float(w.get("end_sec", w_start + 0.3)))
                        w_end = min(end, w_end)
                        if w_end <= w_start:
                            w_end = w_start + 0.1
                        words.append(WordTiming(word=w_word, start_sec=w_start, end_sec=w_end))
            elif transcript:
                words = self.transcriber.estimate_word_timings(transcript, max(1.0, end - start))

            headline = str(raw.get("suggested_headline", "WATCH TILL THE END 😂"))[:100]
            segment = HighlightSegment(
                source_video_id=video.id,
                start_sec=round(start, 2),
                end_sec=round(end, 2),
                humor_score=round(float(raw.get("humor_score", 8.0)), 1),
                summary=str(raw.get("summary", ""))[:200],
                transcript=transcript,
                word_timings=words,
                suggested_headline=headline,
                is_selected=True,
            )
            results.append(segment)

        results.sort(key=lambda s: s.humor_score, reverse=True)
        return results

    def _analyze_via_live(
        self,
        video: SourceVideo,
        clip_count: int,
        min_duration: float,
        max_duration: float,
        config: AppConfig,
    ) -> list[HighlightSegment]:
        """Perform humor analysis using WebSocket Gemini Live API with Tool Calling."""
        api_key = config.google_api_key.get_secret_value()
        client = genai.Client(api_key=api_key)

        pcm_data = self._extract_pcm_16k(video.local_path)
        logger.info(
            "Extracted %d bytes PCM for Live API analysis of %s",
            len(pcm_data),
            video.filename,
        )

        sys_prompt = (
            "You are an expert comedy editor and viral video producer for TikTok / Shorts. "
            "Listen to incoming audio. Find the funniest moments with dialogue, "
            "punchlines, laughs, and reactions. "
            f"Identify up to {clip_count} highlight segments ({min_duration}s to {max_duration}s). "
            "When audio finishes, you MUST execute the report_funny_moments tool with details."
        )

        conf = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            tools=[REPORT_FUNNY_MOMENTS_TOOL],
            system_instruction=types.Content(parts=[types.Part.from_text(text=sys_prompt)]),
        )

        async def run_live() -> list[dict]:
            raw_highlights: list[dict] = []
            async with client.aio.live.connect(model=config.gemini_model, config=conf) as session:
                # Stream PCM in 32000-byte chunks (~1 sec each)
                chunk_size = 32000
                for i in range(0, len(pcm_data), chunk_size):
                    chunk = pcm_data[i : i + chunk_size]
                    await session.send(
                        input=types.LiveClientRealtimeInput(
                            media_chunks=[types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")]
                        )
                    )
                    await asyncio.sleep(0.005)

                trigger_msg = (
                    f"Audio playback completed. Total duration: {video.duration_sec:.1f}s. "
                    f"Please analyze comedic moments and call report_funny_moments "
                    f"with up to {clip_count} highlights."
                )
                await session.send(input=trigger_msg, end_of_turn=True)

                async for response in session.receive():
                    if response.tool_call:
                        for fc in response.tool_call.function_calls:
                            if fc.name == "report_funny_moments":
                                raw_highlights = fc.args.get("highlights", [])
                                return raw_highlights
                    if response.server_content and response.server_content.turn_complete:
                        break
            return raw_highlights

        try:
            raw_list = asyncio.run(run_live())
            if not raw_list:
                logger.warning("Live API did not return any highlights tool calls.")
                return []
            return self._parse_raw_highlights(raw_list, video, min_duration)
        except Exception as exc:
            err_str = str(exc)
            if "timeout" in err_str.lower():
                raise AnalysisTimeoutError(f"Live API timed out: {exc}") from exc
            if "429" in err_str or "exhausted" in err_str.lower():
                raise RateLimitError(f"Live API rate limit: {exc}") from exc
            raise AnalysisError(f"Gemini Live API request failed: {exc}") from exc

    def _analyze_via_rest(
        self,
        video: SourceVideo,
        clip_count: int,
        min_duration: float,
        max_duration: float,
        config: AppConfig,
    ) -> list[HighlightSegment]:
        """Perform multimodal humor detection on the video using Gemini REST API."""
        api_key = config.google_api_key.get_secret_value()
        client = genai.Client(api_key=api_key)

        media_to_upload = self._extract_audio_if_large(video.local_path)

        try:
            uploaded_file = client.files.upload(file=str(media_to_upload))
        except Exception as exc:
            raise AnalysisError(f"Failed to upload media to Gemini: {exc}") from exc

        for _ in range(30):
            file_info = client.files.get(name=uploaded_file.name)
            if file_info.state == "ACTIVE":
                break
            if file_info.state == "FAILED":
                raise AnalysisError("Gemini file processing failed for the uploaded media.")
            time.sleep(1.0)

        prompt = self.SYSTEM_PROMPT_TEMPLATE.format(
            clip_count=clip_count,
            min_duration=min_duration,
            max_duration=max_duration,
            duration=video.duration_sec,
        )

        generate_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AnalysisResponseSchema,
            temperature=0.3,
        )

        last_error: Exception | None = None
        for attempt in range(4):
            try:
                response = client.models.generate_content(
                    model=config.gemini_model,
                    contents=[uploaded_file, prompt],
                    config=generate_config,
                )
                break
            except Exception as exc:
                err_str = str(exc)
                last_error = exc
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    sleep_time = (2.0**attempt) + 1.0
                    logger.warning(
                        "Gemini 429 rate limit hit, backing off for %.1fs (attempt %d/4)",
                        sleep_time,
                        attempt + 1,
                    )
                    time.sleep(sleep_time)
                    continue
                if "timeout" in err_str.lower() or "deadline" in err_str.lower():
                    raise AnalysisTimeoutError(f"Gemini analysis timed out: {exc}") from exc
                if "safety" in err_str.lower() or "blocked" in err_str.lower():
                    raise ContentFilteredError(f"Gemini flagged video content: {exc}") from exc
                raise AnalysisError(f"Gemini API request failed: {exc}") from exc
        else:
            raise RateLimitError("Gemini API rate limit exceeded after retries.") from last_error

        with contextlib.suppress(Exception):
            client.files.delete(name=uploaded_file.name)

        response_text = response.text
        if not response_text:
            raise SchemaValidationError("Gemini returned an empty response.")

        try:
            parsed_data = json.loads(response_text)
            validated_response = AnalysisResponseSchema.model_validate(parsed_data)
        except Exception as exc:
            raise SchemaValidationError(
                f"Failed to validate Gemini response schema: {exc}",
                details=response_text[:500],
            ) from exc

        raw_dicts = [h.model_dump() for h in validated_response.highlights]
        return self._parse_raw_highlights(raw_dicts, video, min_duration)

    def analyze(
        self,
        video: SourceVideo,
        clip_count: int,
        min_duration: float,
        max_duration: float,
        config: AppConfig,
    ) -> list[HighlightSegment]:
        """Analyze video using either Live API or REST depending on configured model."""
        is_live = (
            "native-audio" in config.gemini_model.lower()
            or "live" in config.gemini_model.lower()
        )
        if is_live:
            logger.info("Using Gemini Live API engine with model: %s", config.gemini_model)
            return self._analyze_via_live(
                video=video,
                clip_count=clip_count,
                min_duration=min_duration,
                max_duration=max_duration,
                config=config,
            )
        logger.info("Using Gemini REST Files API engine with model: %s", config.gemini_model)
        return self._analyze_via_rest(
            video=video,
            clip_count=clip_count,
            min_duration=min_duration,
            max_duration=max_duration,
            config=config,
        )

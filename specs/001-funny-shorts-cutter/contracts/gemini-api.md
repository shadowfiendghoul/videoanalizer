# Gemini API Contract: Humor Detection & Transcription

**Feature**: `001-funny-shorts-cutter` | **Date**: 2026-10-10

## Overview

Single multimodal API call to Gemini 2.5 Flash using Native Audio Dialog mode. The video file (or audio extract for large files) is sent as inline content. The model returns structured JSON with detected funny moments, word-level transcription, and hook headline suggestions.

---

## Request Contract

**SDK**: `google-genai` official Python SDK
**Model**: `gemini-2.5-flash`
**Method**: `client.models.generate_content()`

### Input Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | `str` | `"gemini-2.5-flash"` |
| `contents` | `list[Content]` | Video/audio file as `Part` + system prompt as text `Part` |
| `config` | `GenerateContentConfig` | `response_mime_type="application/json"`, `response_schema=AnalysisResponse`, timeout, safety settings |

### System Prompt Template

```text
You are a comedy content analyst. Analyze this video for the funniest moments
with spoken dialogue.

Return EXACTLY {clip_count} highlight segments, each between {min_duration}
and {max_duration} seconds long.

For each highlight, provide:
1. Precise start and end timestamps (in seconds, decimal)
2. A humor score from 0.0 to 10.0
3. A brief summary of why this moment is funny (max 200 characters)
4. Full dialogue transcript for the segment
5. Word-level timing: each spoken word with its start and end time
   (relative to segment start)
6. A catchy, viral hook headline for TikTok/Shorts (max 100 characters)

Focus on: punchlines, unexpected reactions, comedic timing, laughter moments,
absurd statements, and audience-engaging dialogue peaks.

If fewer than {clip_count} genuinely funny moments exist, return as many as
detected with a note. Never fabricate timestamps.

Respond in valid JSON matching the provided schema.
```

---

## Response Contract

### Expected JSON Schema (Pydantic model for `response_schema`)

```json
{
  "type": "object",
  "properties": {
    "highlights": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "start_sec": { "type": "number", "description": "Start timestamp in seconds" },
          "end_sec": { "type": "number", "description": "End timestamp in seconds" },
          "humor_score": { "type": "number", "minimum": 0.0, "maximum": 10.0 },
          "summary": { "type": "string", "maxLength": 200 },
          "transcript": { "type": "string" },
          "word_timings": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "word": { "type": "string" },
                "start_sec": { "type": "number" },
                "end_sec": { "type": "number" }
              },
              "required": ["word", "start_sec", "end_sec"]
            }
          },
          "suggested_headline": { "type": "string", "maxLength": 100 }
        },
        "required": ["start_sec", "end_sec", "humor_score", "summary", "transcript", "word_timings", "suggested_headline"]
      }
    },
    "video_language": { "type": "string", "description": "Detected primary language code (e.g. 'ru', 'en')" },
    "analysis_notes": { "type": "string", "description": "Optional notes about detection quality or limitations" }
  },
  "required": ["highlights"]
}
```

---

## Error Handling

| Error Scenario | Expected Behavior |
|---------------|-------------------|
| API key invalid / missing | Raise `ConfigurationError` with clear message. Never expose key value in error. |
| Rate limit exceeded (429) | Retry with exponential backoff (base 2s, max 3 retries, jitter). Raise `RateLimitError` if exhausted. |
| Timeout (>120s) | Raise `AnalysisTimeoutError`. Suggest retry or shorter video. |
| Model returns invalid JSON | Raise `SchemaValidationError` with raw response for debugging. |
| Model returns 0 highlights | Return empty list. UI displays "no funny moments detected" message. |
| Video too large for API | Extract audio-only track via FFmpeg, retry with audio. If still too large, chunk into segments. |
| Safety filter blocks response | Raise `ContentFilteredError`. Suggest different video content. |

---

## Mock Response (for testing)

```json
{
  "highlights": [
    {
      "start_sec": 45.2,
      "end_sec": 78.5,
      "humor_score": 8.7,
      "summary": "Streamer accidentally walks off cliff while explaining strategy, panics audibly",
      "transcript": "So the key to winning here is you just need to carefully walk along the edge and OH NO NO NO WAIT",
      "word_timings": [
        {"word": "So", "start_sec": 0.0, "end_sec": 0.2},
        {"word": "the", "start_sec": 0.2, "end_sec": 0.35},
        {"word": "key", "start_sec": 0.35, "end_sec": 0.55},
        {"word": "to", "start_sec": 0.55, "end_sec": 0.65},
        {"word": "winning", "start_sec": 0.65, "end_sec": 1.0},
        {"word": "here", "start_sec": 1.0, "end_sec": 1.2},
        {"word": "is", "start_sec": 1.2, "end_sec": 1.35}
      ],
      "suggested_headline": "He really said 'carefully' 💀😂"
    }
  ],
  "video_language": "en",
  "analysis_notes": "Detected 1 high-confidence comedic moment in the provided segment."
}
```

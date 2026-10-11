"""Highlight models representing detected comedic segments and word-level timings."""

from uuid import uuid4
from pydantic import BaseModel, Field, computed_field, model_validator


class WordTiming(BaseModel):
    """Word-level timing information for karaoke subtitle synchronization."""

    word: str = Field(
        ...,
        min_length=1,
        description="Spoken word text.",
    )
    start_sec: float = Field(
        ...,
        ge=0.0,
        description="Word start timestamp relative to highlight segment start (seconds).",
    )
    end_sec: float = Field(
        ...,
        gt=0.0,
        description="Word end timestamp relative to highlight segment start (seconds).",
    )

    @model_validator(mode="after")
    def validate_timing_order(self) -> "WordTiming":
        """Ensure end time is strictly greater than start time."""
        if self.end_sec <= self.start_sec:
            raise ValueError(
                f"end_sec ({self.end_sec}) must be greater than start_sec ({self.start_sec})"
            )
        return self


class HighlightSegment(BaseModel):
    """A detected funny moment segment within the source video."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the highlight clip.",
    )
    source_video_id: str = Field(
        ...,
        description="Foreign key identifier referencing the parent SourceVideo.",
    )
    start_sec: float = Field(
        ...,
        ge=0.0,
        description="Highlight start time in the source video (seconds).",
    )
    end_sec: float = Field(
        ...,
        gt=0.0,
        description="Highlight end time in the source video (seconds).",
    )
    humor_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="AI-assigned comedy rating from 0.0 to 10.0.",
    )
    summary: str = Field(
        ...,
        max_length=200,
        description="Concise description of the comedic action or punchline.",
    )
    transcript: str = Field(
        ...,
        description="Full spoken dialogue transcript for this segment.",
    )
    word_timings: list[WordTiming] = Field(
        default_factory=list,
        description="List of words with relative start/end timestamps for karaoke captions.",
    )
    suggested_headline: str = Field(
        ...,
        max_length=100,
        description="AI-generated catchy hook headline for the top banner.",
    )
    is_selected: bool = Field(
        default=True,
        description="Whether this highlight is currently selected by the user for rendering.",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def duration_sec(self) -> float:
        """Computed duration of the highlight segment in seconds."""
        return round(self.end_sec - self.start_sec, 3)

    @model_validator(mode="after")
    def validate_segment_bounds(self) -> "HighlightSegment":
        """Ensure end timestamp is strictly after start timestamp."""
        if self.end_sec <= self.start_sec:
            raise ValueError(
                f"end_sec ({self.end_sec}) must be greater than start_sec ({self.start_sec})"
            )
        return self

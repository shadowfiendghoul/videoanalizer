"""Layout preset and cropping coordinate models for vertical 9:16 reformatting."""

from typing import Literal
from pydantic import BaseModel, Field, model_validator


class CropBox(BaseModel):
    """Bounding box coordinates for cropping within source video frames."""

    x: int = Field(
        default=0,
        ge=0,
        description="Top-left corner X coordinate (pixels).",
    )
    y: int = Field(
        default=0,
        ge=0,
        description="Top-left corner Y coordinate (pixels).",
    )
    width: int = Field(
        ...,
        gt=0,
        description="Crop width (pixels).",
    )
    height: int = Field(
        ...,
        gt=0,
        description="Crop height (pixels).",
    )


class LayoutPreset(BaseModel):
    """Configuration defining how 16:9 source content maps to vertical 9:16 canvas."""

    mode: Literal["center_crop", "split_screen"] = Field(
        default="center_crop",
        description="Layout strategy: 'center_crop' or 'split_screen'.",
    )
    webcam_box: CropBox | None = Field(
        default=None,
        description="Crop boundary box for streamer facecam/reaction in split screen mode.",
    )
    gameplay_box: CropBox | None = Field(
        default=None,
        description="Crop boundary box for primary gameplay/content in split screen mode.",
    )
    webcam_position: Literal["top", "bottom"] = Field(
        default="top",
        description="Placement of webcam in vertical stack ('top' or 'bottom').",
    )

    @model_validator(mode="after")
    def validate_split_screen_boxes(self) -> "LayoutPreset":
        """Ensure both crop boxes are present when split_screen mode is active."""
        if self.mode == "split_screen":
            if self.webcam_box is None:
                raise ValueError("webcam_box is required when mode is 'split_screen'")
            if self.gameplay_box is None:
                raise ValueError("gameplay_box is required when mode is 'split_screen'")
        return self

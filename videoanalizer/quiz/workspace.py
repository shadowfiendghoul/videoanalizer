"""Task-scoped workspace manager with deterministic resource cleanup."""

import logging
import shutil
import uuid
from pathlib import Path
from types import TracebackType

from videoanalizer.quiz.config import QuizConfig, get_quiz_config

logger = logging.getLogger(__name__)


class QuizWorkspace:
    """Context manager isolating temporary media files for a quiz generation job.

    Ensures that temporary audio slices, downloaded images, and Remotion input props
    are deterministically cleaned up from disk upon job termination or error.
    """

    def __init__(
        self,
        job_id: str | None = None,
        base_dir: Path | None = None,
        auto_cleanup: bool = True,
        config: QuizConfig | None = None,
    ) -> None:
        self.job_id = job_id or f"quiz_{uuid.uuid4().hex[:10]}"
        self.config = config or get_quiz_config()
        root_base = base_dir or self.config.temp_dir
        self.root_dir = root_base / self.job_id
        self.public_dir = self.root_dir / "public"
        self.audio_dir = self.public_dir / "audio"
        self.images_dir = self.public_dir / "images"
        self.auto_cleanup = auto_cleanup
        self._is_cleaned_up = False

    @property
    def path(self) -> Path:
        """Alias for root_dir."""
        return self.root_dir

    def __enter__(self) -> "QuizWorkspace":
        self.setup()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.auto_cleanup:
            self.cleanup()

    async def __aenter__(self) -> "QuizWorkspace":
        self.setup()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.auto_cleanup:
            self.cleanup()

    def setup(self) -> None:
        """Create workspace directory structure."""
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self._is_cleaned_up = False
        logger.debug(f"Created isolated quiz workspace: {self.root_dir}")

    def cleanup(self) -> None:
        """Safely delete the workspace directory and all contained files."""
        if self._is_cleaned_up:
            return
        if self.root_dir.exists():
            try:
                shutil.rmtree(self.root_dir, ignore_errors=True)
                logger.debug(f"Cleaned up quiz workspace: {self.root_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanly remove workspace {self.root_dir}: {e}")
        self._is_cleaned_up = True

    def get_audio_path(self, filename: str) -> Path:
        """Return full path for a temporary audio file."""
        return self.audio_dir / filename

    def get_image_path(self, filename: str) -> Path:
        """Return full path for a downloaded temporary image file."""
        return self.images_dir / filename

    def get_props_path(self) -> Path:
        """Return full path for serialized remotion-props.json."""
        return self.root_dir / "remotion-props.json"

"""Session-scoped temporary workspace directory manager with deterministic cleanup."""

import shutil
import tempfile
import time
from pathlib import Path
from types import TracebackType
from uuid import uuid4


class SessionTempDir:
    """Context manager and helper managing an isolated temporary folder for a session."""

    def __init__(self, base_dir: Path | None = None, prefix: str = "va_session_") -> None:
        self.session_id = str(uuid4())
        self._base_dir = base_dir
        self._prefix = prefix
        self._path: Path | None = None

    @property
    def path(self) -> Path:
        """Return the created session temp path; creates directory if not yet created."""
        if self._path is None:
            if self._base_dir is not None:
                self._base_dir.mkdir(parents=True, exist_ok=True)
                target = self._base_dir / f"{self._prefix}{self.session_id}"
                target.mkdir(parents=True, exist_ok=True)
                self._path = target
            else:
                raw_path = tempfile.mkdtemp(prefix=self._prefix)
                self._path = Path(raw_path)
        return self._path

    def cleanup(self) -> None:
        """Recursively delete the temporary directory handling Windows file locking gracefully."""
        if self._path is not None and self._path.exists():
            for attempt in range(3):
                try:
                    shutil.rmtree(self._path, ignore_errors=False)
                    break
                except (PermissionError, OSError):
                    time.sleep(0.1 * (attempt + 1))
            else:
                # Fallback: remove whatever is possible without crashing
                shutil.rmtree(self._path, ignore_errors=True)
            self._path = None

    def __enter__(self) -> "SessionTempDir":
        # Access path to ensure creation
        _ = self.path
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.cleanup()

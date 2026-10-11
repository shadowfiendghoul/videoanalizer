"""Media ingestion service supporting YouTube downloading and local video validation."""

import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from videoanalizer.exceptions import DownloadError, UnsupportedFormatError
from videoanalizer.media.probe import probe_video
from videoanalizer.models.source_video import SourceVideo

ALLOWED_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm"}
YOUTUBE_DOMAINS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


class IngestionService:
    """Service handling YouTube video downloading and local video ingestion."""

    @staticmethod
    def is_youtube_url(url_or_path: str) -> bool:
        """Check if the provided input string is a valid YouTube URL."""
        cleaned = url_or_path.strip()
        if not (cleaned.startswith("http://") or cleaned.startswith("https://")):
            return False

        try:
            parsed = urlparse(cleaned)
            return parsed.netloc.lower() in YOUTUBE_DOMAINS or "youtube" in parsed.netloc.lower()
        except Exception:
            return False

    def download_youtube(self, url: str, dest_dir: Path) -> Path:
        """Download video from YouTube using yt-dlp CLI subprocess.

        Args:
            url: YouTube video URL.
            dest_dir: Target directory to save downloaded media.

        Returns:
            Path to the downloaded MP4 file.

        Raises:
            DownloadError: If yt-dlp is missing or the download process fails.
        """
        ytdlp_bin = shutil.which("yt-dlp")
        if not ytdlp_bin:
            raise DownloadError(
                "yt-dlp executable not found. Ensure 'yt-dlp' is installed in the python environment."
            )

        dest_dir.mkdir(parents=True, exist_ok=True)
        output_template = str(dest_dir / "%(id)s.%(ext)s")

        cmd = [
            ytdlp_bin,
            "--no-playlist",
            "--extractor-args",
            "youtube:player_client=ios,android,web",
            "--retries",
            "5",
            "--fragment-retries",
            "5",
            "--file-access-retries",
            "5",
            "--retry-sleep",
            "1",
            "--socket-timeout",
            "30",
            "-f",
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/bestvideo+bestaudio/best",
            "--merge-output-format",
            "mp4",
            "-o",
            output_template,
            url,
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as exc:
            raise DownloadError(f"Failed to execute yt-dlp download: {exc}") from exc

        if proc.returncode != 0:
            error_msg = proc.stderr.strip() or proc.stdout.strip()
            raise DownloadError(
                f"Failed to download YouTube video from '{url}'",
                details=error_msg,
            )

        # Locate downloaded file in dest_dir
        downloaded_files = list(dest_dir.glob("*.mp4"))
        if not downloaded_files:
            # Fallback check any video format
            downloaded_files = [
                f for f in dest_dir.iterdir() if f.suffix.lower() in ALLOWED_EXTENSIONS
            ]

        if not downloaded_files:
            raise DownloadError("yt-dlp completed successfully but output video file was not found")

        # Return the newest downloaded file
        downloaded_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return downloaded_files[0]

    def validate_local_file(self, path: Path) -> None:
        """Validate that a local media file exists and has a supported format.

        Args:
            path: Path to the local video file.

        Raises:
            UnsupportedFormatError: If the file does not exist, has an unsupported extension,
                                   or cannot be probed by FFmpeg.
        """
        if not path.exists():
            raise UnsupportedFormatError(f"Local video file not found at {path}")

        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise UnsupportedFormatError(
                f"Unsupported video file extension '{path.suffix}'. "
                f"Allowed formats are: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        try:
            probe_video(path)
        except Exception as exc:
            raise UnsupportedFormatError(
                f"Media validation failed for '{path.name}': {exc}"
            ) from exc

    def ingest(self, source: str, session_dir: Path) -> SourceVideo:
        """Ingest video from either a YouTube URL or a local path.

        Args:
            source: YouTube URL string or path to local video file.
            session_dir: Session temporary directory to hold downloaded or processed files.

        Returns:
            Populated SourceVideo domain model instance.

        Raises:
            DownloadError: If YouTube download fails.
            UnsupportedFormatError: If local file format is invalid.
        """
        source_clean = source.strip()

        if self.is_youtube_url(source_clean):
            download_dir = session_dir / "download"
            video_path = self.download_youtube(source_clean, download_dir)
            meta = probe_video(video_path)

            return SourceVideo(
                origin="youtube",
                original_url=source_clean,
                local_path=video_path,
                filename=video_path.name,
                duration_sec=meta["duration_sec"],
                width=meta["width"],
                height=meta["height"],
                fps=meta["fps"],
                codec=meta["codec"],
                audio_codec=meta["audio_codec"],
                file_size_bytes=meta["file_size_bytes"],
            )

        # Local file ingestion
        local_path = Path(source_clean).resolve()
        self.validate_local_file(local_path)
        meta = probe_video(local_path)

        return SourceVideo(
            origin="local",
            original_url=None,
            local_path=local_path,
            filename=local_path.name,
            duration_sec=meta["duration_sec"],
            width=meta["width"],
            height=meta["height"],
            fps=meta["fps"],
            codec=meta["codec"],
            audio_codec=meta["audio_codec"],
            file_size_bytes=meta["file_size_bytes"],
        )

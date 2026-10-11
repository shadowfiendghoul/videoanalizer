"""Full video short composition and rendering engine orchestrating all media stages."""

import shutil
from collections.abc import Callable
from pathlib import Path

from videoanalizer.exceptions import RenderError
from videoanalizer.media.clipper import extract_clip
from videoanalizer.media.overlay import add_banner
from videoanalizer.media.reframer import Reframer
from videoanalizer.media.silence_cutter import cut_silences
from videoanalizer.media.subtitler import burn_subtitles, generate_ass_subtitles
from videoanalizer.models.render_job import ClipRenderJob
from videoanalizer.models.source_video import SourceVideo
from videoanalizer.services.silence import SilenceDetector
from videoanalizer.services.transcriber import TranscriptionService


class Renderer:
    """Orchestrates end-to-end rendering pipeline for a single vertical short video."""

    def __init__(self) -> None:
        self.reframer = Reframer()
        self.silence_detector = SilenceDetector()
        self.transcription_service = TranscriptionService()

    def render(
        self,
        job: ClipRenderJob,
        source_video: SourceVideo,
        session_dir: Path,
        final_output_dir: Path | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> Path:
        """Render the complete vertical short from source video through all configured effects.

        Pipeline Stages:
            1. Extract highlight segment from source media.
            2. Reframe to 9:16 vertical canvas (Center Crop or Streamer Split Screen).
            3. Trim audio dead air with padded micro-crossfades (if enabled).
            4. Burn dynamic TikTok karaoke subtitles (if enabled).
            5. Overlay top hook headline banner (if enabled).
            6. Move rendered video to final output directory.

        Args:
            job: ClipRenderJob specification with all styling and effects configurations.
            source_video: SourceVideo domain model containing local media path.
            session_dir: Isolated session workspace for intermediate files.
            final_output_dir: Destination folder for the finished MP4 file.
            progress_callback: Optional callable(percent: int, stage_text: str) for progress.

        Returns:
            Absolute Path to the rendered MP4 file.

        Raises:
            RenderError: If any pipeline stage fails.
        """
        job.status = "rendering"
        job.error_message = None

        workspace = session_dir / f"job_{job.id}"
        workspace.mkdir(parents=True, exist_ok=True)

        try:
            # Stage 1: Extract highlight clip
            if progress_callback:
                progress_callback(30, "Кадрирование 9:16 и обрезка пауз через FFmpeg...")
            step1_clip = workspace / "step1_raw_clip.mp4"
            extract_clip(
                source_path=source_video.local_path,
                start_sec=job.highlight.start_sec,
                end_sec=job.highlight.end_sec,
                output_path=step1_clip,
            )

            # Stage 2: Reframe to 9:16 (1080x1920)
            if progress_callback:
                progress_callback(45, "Кадрирование 9:16 и обрезка пауз через FFmpeg...")
            step2_reframed = workspace / "step2_reframed.mp4"
            is_split = (
                job.layout.mode == "split_screen"
                and job.layout.webcam_box
                and job.layout.gameplay_box
            )
            if is_split:
                self.reframer.split_screen(
                    input_path=step1_clip,
                    output_path=step2_reframed,
                    webcam_box=job.layout.webcam_box,
                    gameplay_box=job.layout.gameplay_box,
                    webcam_position=job.layout.webcam_position,
                    target_w=job.output_width,
                    target_h=job.output_height,
                )
            else:
                self.reframer.center_crop(
                    input_path=step1_clip,
                    output_path=step2_reframed,
                    target_w=job.output_width,
                    target_h=job.output_height,
                )

            current_video = step2_reframed

            # Stage 3: Silence trimming
            if job.silence.enabled:
                if progress_callback:
                    progress_callback(60, "Кадрирование 9:16 и обрезка пауз через FFmpeg...")
                step3_silence = workspace / "step3_silence_cut.mp4"
                silences = self.silence_detector.detect_silences(current_video, job.silence)
                keep_segments = self.silence_detector.compute_keep_segments(
                    duration=job.highlight.duration_sec,
                    silences=silences,
                    padding_ms=job.silence.padding_ms,
                )
                cut_silences(
                    input_path=current_video,
                    keep_segments=keep_segments,
                    output_path=step3_silence,
                    crossfade_ms=job.silence.crossfade_ms,
                )
                current_video = step3_silence

            # Stage 4: Subtitles
            if job.subtitles_enabled:
                if progress_callback:
                    progress_callback(75, "Генерация караоке-субтитров...")
                step4_subs = workspace / "step4_subtitled.mp4"
                words = self.transcription_service.get_word_timings(job.highlight)
                if words:
                    ass_text = generate_ass_subtitles(
                        word_timings=words,
                        style=job.subtitles,
                        frame_width=job.output_width,
                        frame_height=job.output_height,
                    )
                    burn_subtitles(current_video, ass_text, step4_subs)
                    current_video = step4_subs

            # Stage 5: Banner overlay
            if job.banner.enabled and job.banner.text.strip():
                if progress_callback:
                    progress_callback(88, "Генерация караоке-субтитров...")
                step5_banner = workspace / "step5_banner.mp4"
                add_banner(
                    video_path=current_video,
                    banner=job.banner,
                    output_path=step5_banner,
                    frame_width=job.output_width,
                )
                current_video = step5_banner

            # Stage 6: Copy to final output location
            out_dir = final_output_dir or (session_dir / "output")
            out_dir.mkdir(parents=True, exist_ok=True)

            safe_chars = (c for c in source_video.filename if c.isalnum() or c in ("-", "_"))
            safe_stem = "".join(safe_chars).rstrip()
            final_filename = f"short_{safe_stem}_{int(job.highlight.start_sec)}s_{job.id[:6]}.mp4"
            final_path = out_dir / final_filename

            shutil.copy2(current_video, final_path)

            if progress_callback:
                progress_callback(100, "Готово к скачиванию!")

            job.status = "complete"
            job.output_path = final_path
            return final_path

        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            raise RenderError(f"Rendering failed for highlight {job.highlight.id}: {exc}") from exc

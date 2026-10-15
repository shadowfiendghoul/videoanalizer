"""QuizOrchestrator coordinates trivia generation, audio synthesis, Remotion video, and cleanup."""

import asyncio
import json
import logging
import os
import re
import secrets
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from datetime import UTC, datetime
from videoanalizer.media.uniquifier import VideoUniquifierConfig, apply_video_uniquifier
from videoanalizer.quiz.audio_service import AudioService
from videoanalizer.quiz.config import QuizConfig, ensure_system_paths, get_quiz_config
from videoanalizer.quiz.image_service import ImageService
from videoanalizer.quiz.models import (
    QuizChallenge,
    QuizRetentionConfig,
    RemotionRenderProps,
    RenderProfile,
    SfxPaths,
    VisualQuizDataset,
    VisualQuizRenderProps,
    VoiceConfig,
)
from videoanalizer.quiz.script_service import ScriptService
from videoanalizer.quiz.workspace import QuizWorkspace
from videoanalizer.utils.hardware import (
    calculate_optimal_concurrency,
    get_hardware_capabilities,
)

logger = logging.getLogger(__name__)

# Global FIFO Semaphore to prevent multiple concurrent Remotion instances and OOM on iGPU
_RENDER_SEMAPHORE: asyncio.Semaphore | None = None


def get_render_semaphore() -> asyncio.Semaphore:
    """Lazily initialize asyncio.Semaphore(1) on active event loop."""
    global _RENDER_SEMAPHORE
    if _RENDER_SEMAPHORE is None:
        _RENDER_SEMAPHORE = asyncio.Semaphore(1)
    return _RENDER_SEMAPHORE


class QuizOrchestrator:
    """Orchestrator for the complete vertical quiz short generation pipeline."""

    _recent_random_backgrounds: list[Path] = []

    def __init__(self, config: QuizConfig | None = None) -> None:
        self.config = config or get_quiz_config()
        self.script_service = ScriptService(config=self.config)
        self.audio_service = AudioService(config=self.config)
        self.image_service = ImageService()

    def _pick_from_candidates(
        self,
        candidates: list[Path],
        exclude_paths: list[Path | str] | None = None,
    ) -> Path:
        """Pick a background from candidates adhering to exclusion and recent usage history."""
        if not candidates:
            raise FileNotFoundError("Candidate list is empty")
        if len(candidates) == 1:
            return candidates[0]

        excluded_set: set[Path] = set()
        if exclude_paths:
            for ep in exclude_paths:
                p_ep = Path(ep)
                excluded_set.add(p_ep)
                excluded_set.add(p_ep.resolve())
                excluded_set.add(self.config.backgrounds_dir / p_ep.name)

        recent = QuizOrchestrator._recent_random_backgrounds
        fresh = [f for f in candidates if f not in excluded_set and f not in recent]
        if not fresh:
            fresh = [f for f in candidates if f not in excluded_set]
        if not fresh:
            fresh = candidates

        if len(fresh) > 1 and recent:
            last_used = recent[-1]
            non_last = [f for f in fresh if f != last_used]
            if non_last:
                fresh = non_last

        picked = secrets.choice(fresh)
        QuizOrchestrator._recent_random_backgrounds.append(picked)
        max_history = max(1, len(candidates) - 1)
        while len(QuizOrchestrator._recent_random_backgrounds) > max_history:
            QuizOrchestrator._recent_random_backgrounds.pop(0)

        return picked

    def select_background(
        self,
        explicit_path: Path | str | None = None,
        exclude_paths: list[Path | str] | None = None,
    ) -> Path:
        """Select a vertical background video, either specific, from a chosen folder, or random."""
        bg_dir = self.config.backgrounds_dir

        # Case 1: Explicit folder selected (e.g. "folder:pastel" or "folder:gameplay")
        if explicit_path and str(explicit_path).strip().lower().startswith("folder:"):
            folder_name = str(explicit_path).strip()[7:].strip()
            target_folder = bg_dir / folder_name
            if target_folder.exists() and target_folder.is_dir():
                folder_candidates = [
                    f for f in target_folder.glob("*.mp4")
                    if not f.name.startswith(".") and f.is_file()
                ]
                if folder_candidates:
                    return self._pick_from_candidates(folder_candidates, exclude_paths)
            logger.warning(
                "Explicit background folder '%s' not found or empty, falling back to random background",
                folder_name,
            )

        # Case 2: Explicit specific file path (e.g. "pastel/mint_stars.mp4" or "minecraft_parkour_1.mp4")
        if explicit_path and str(explicit_path).strip().lower() != "random":
            p = Path(explicit_path)
            if p.exists() and p.is_file():
                return p
            p_in_bg = bg_dir / explicit_path
            if p_in_bg.exists() and p_in_bg.is_file():
                return p_in_bg
            # If path points directly to a directory
            if p_in_bg.exists() and p_in_bg.is_dir():
                dir_candidates = [
                    f for f in p_in_bg.glob("*.mp4")
                    if not f.name.startswith(".") and f.is_file()
                ]
                if dir_candidates:
                    return self._pick_from_candidates(dir_candidates, exclude_paths)
            logger.warning(
                "Explicit background '%s' not found, falling back to random background",
                explicit_path,
            )

        # Case 3: Random selection from entire collection (root + subfolders)
        if bg_dir.exists():
            all_candidates = [
                f for f in bg_dir.glob("*.mp4")
                if not f.name.startswith(".") and f.is_file()
            ]
            if not all_candidates:
                all_candidates = [
                    f for f in bg_dir.rglob("*.mp4")
                    if not f.name.startswith(".") and f.is_file()
                ]
            if all_candidates:
                return self._pick_from_candidates(all_candidates, exclude_paths)

        default_bg = bg_dir / "default_bg.mp4"
        if default_bg.exists():
            return default_bg

        raise FileNotFoundError(
            f"No background videos found in {bg_dir}. "
            f"Please place a 9:16 background video in {bg_dir}."
        )

    def _probe_video_duration_sec(self, video_path: Path) -> float:
        """Probe video duration in seconds using ffprobe."""
        ensure_system_paths()
        ffprobe_bin = shutil.which("ffprobe")
        if not ffprobe_bin:
            return 0.0
        try:
            cmd = [
                ffprobe_bin,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(video_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603
            data = json.loads(res.stdout)
            return float(data["format"]["duration"])
        except Exception as exc:
            logger.debug("Could not probe video duration for %s: %s", video_path, exc)
            return 0.0

    def _probe_video_duration_frames(self, video_path: Path, fps: int = 60) -> int:
        """Probe video duration and calculate duration in frames."""
        dur_sec = self._probe_video_duration_sec(video_path)
        if dur_sec <= 0.0:
            return fps * 5
        return max(1, int(dur_sec * fps))

    def _probe_video_dimensions(self, video_path: Path) -> tuple[int, int]:
        """Probe video width and height in pixels using ffprobe."""
        ensure_system_paths()
        ffprobe_bin = shutil.which("ffprobe")
        if not ffprobe_bin:
            return 0, 0
        try:
            cmd = [
                ffprobe_bin,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "json",
                str(video_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603
            data = json.loads(res.stdout)
            streams = data.get("streams", [])
            if streams and "width" in streams[0] and "height" in streams[0]:
                return int(streams[0]["width"]), int(streams[0]["height"])
            return 0, 0
        except Exception as exc:
            logger.debug("Could not probe video dimensions for %s: %s", video_path, exc)
            return 0, 0

    def _prepare_background(
        self,
        bg_source: Path,
        target_bg: Path,
        duration_sec: float = 120.0,
        background_mode: str = "loop",
        folder_scope: str | Path | None = None,
    ) -> str:
        """Stage background video into public dir.

        If background_mode == "loop" (default):
            Loops the selected background video cleanly for the entire duration_sec using -stream_loop -1.
        If background_mode == "random_switch":
            When the background video ends (or if single clip is too long, every 12-15s),
            smoothly switches to another random background video from the chosen folder or library.
        """
        ensure_system_paths()
        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            shutil.copy2(bg_source, target_bg)
            return target_bg.name

        dur_initial = self._probe_video_duration_sec(bg_source)

        # Mode A: "loop" (Зацикливание одного фона)
        if background_mode != "random_switch":
            try:
                cmd_loop = [
                    ffmpeg_bin,
                    "-y",
                    "-stream_loop",
                    "-1",
                    "-i",
                    str(bg_source),
                    "-t",
                    f"{duration_sec:.1f}",
                    "-c",
                    "copy",
                    str(target_bg),
                ]
                subprocess.run(cmd_loop, capture_output=True, check=True)  # noqa: S603
                return target_bg.name
            except Exception as loop_err:
                logger.warning("Single background stream loop failed (%s), copying", loop_err)
                shutil.copy2(bg_source, target_bg)
                return target_bg.name

        # Mode B: "random_switch" (Случайная смена при конце)
        if dur_initial > 15.0:
            # If the source video is very long (e.g. 5-minute gameplay), slice first segment to ~12s
            # so the random switch actually triggers within the short video!
            dur_initial = 12.0

        bg_dir = self.config.backgrounds_dir
        # Scope candidates strictly to chosen folder if specified, or to parent folder of bg_source
        cand_dir: Path | None = None
        if folder_scope and str(folder_scope).strip().lower().startswith("folder:"):
            folder_name = str(folder_scope).strip()[7:].strip()
            folder_path = bg_dir / folder_name
            if folder_path.exists() and folder_path.is_dir():
                cand_dir = folder_path
        elif folder_scope and (bg_dir / str(folder_scope)).is_dir():
            cand_dir = bg_dir / str(folder_scope)
        elif bg_source.parent.resolve() != bg_dir.resolve():
            cand_dir = bg_source.parent

        if cand_dir and cand_dir.exists():
            all_candidates = [
                p for p in cand_dir.glob("*.mp4")
                if not p.name.startswith(".") and p.is_file()
            ]
        else:
            all_candidates = (
                [
                    p for p in bg_dir.glob("*.mp4")
                    if not p.name.startswith(".") and p.is_file()
                ]
                if bg_dir.exists()
                else []
            )
            if not all_candidates and bg_dir.exists():
                all_candidates = [
                    p for p in bg_dir.rglob("*.mp4")
                    if not p.name.startswith(".") and p.is_file()
                ]

        if not all_candidates:
            all_candidates = [bg_source]

        playlist: list[Path] = [bg_source]
        accumulated_sec = dur_initial
        used_in_video: set[Path] = {bg_source}
        last_picked = bg_source

        while accumulated_sec < duration_sec and len(playlist) < 60:
            # First priority: pick candidates that have NOT been used in this video yet
            unused_candidates = [p for p in all_candidates if p not in used_in_video]
            if unused_candidates:
                next_bg = secrets.choice(unused_candidates)
            else:
                # All available candidates in the folder have already been used at least once.
                # Start new cycle, strictly avoiding repeating the immediate last clip.
                recycle_candidates = [p for p in all_candidates if p != last_picked]
                if not recycle_candidates:
                    recycle_candidates = all_candidates
                next_bg = secrets.choice(recycle_candidates)
                used_in_video = {last_picked}

            dur_next = self._probe_video_duration_sec(next_bg)
            if dur_next <= 0.0:
                dur_next = max(10.0, dur_initial)
            playlist.append(next_bg)
            used_in_video.add(next_bg)
            accumulated_sec += dur_next
            last_picked = next_bg

        # If playlist ended up with only 1 clip, simple loop
        if len(playlist) <= 1:
            try:
                cmd_loop = [
                    ffmpeg_bin,
                    "-y",
                    "-stream_loop",
                    "-1",
                    "-i",
                    str(bg_source),
                    "-t",
                    f"{duration_sec:.1f}",
                    "-c",
                    "copy",
                    str(target_bg),
                ]
                subprocess.run(cmd_loop, capture_output=True, check=True)  # noqa: S603
                return target_bg.name
            except Exception:
                shutil.copy2(bg_source, target_bg)
                return target_bg.name

        logger.info(
            "Background video '%s' duration (%.1fs) < %.1fs. Chaining %d clips from %s.",
            bg_source.name,
            dur_initial,
            duration_sec,
            len(playlist),
            bg_dir,
        )

        staged_ok = False
        concat_file = target_bg.parent / f"_concat_{target_bg.stem}.txt"
        try:
            # 1. Try fast concat demuxer with stream copy
            lines = [f"file '{p.resolve().as_posix()}'" for p in playlist]
            concat_file.write_text("\n".join(lines), encoding="utf-8")

            cmd_concat = [
                ffmpeg_bin,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-t",
                f"{duration_sec:.1f}",
                "-c",
                "copy",
                str(target_bg),
            ]
            subprocess.run(cmd_concat, capture_output=True, check=True)  # noqa: S603
            staged_ok = target_bg.exists() and target_bg.stat().st_size > 0
        except Exception as demux_err:
            logger.debug(
                "Concat demuxer copy failed (%s), normalizing with filter_complex",
                demux_err,
            )
        finally:
            concat_file.unlink(missing_ok=True)

        # 2. If concat demuxer failed (different codecs/resolutions), re-encode with filter_complex
        if not staged_ok:
            try:
                inputs: list[str] = []
                filters: list[str] = []
                for idx, p in enumerate(playlist):
                    inputs.extend(["-i", str(p)])
                    filters.append(
                        f"[{idx}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                        f"crop=1080:1920,setsar=1,fps={self.config.fps}[v{idx}];"
                    )
                v_tags = "".join(f"[v{i}]" for i in range(len(playlist)))
                filters.append(f"{v_tags}concat=n={len(playlist)}:v=1:a=0[outv]")
                filter_complex_str = " ".join(filters)

                cmd_fc = [
                    ffmpeg_bin,
                    "-y",
                    *inputs,
                    "-filter_complex",
                    filter_complex_str,
                    "-map",
                    "[outv]",
                    "-t",
                    f"{duration_sec:.1f}",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast",
                    "-crf",
                    "22",
                    str(target_bg),
                ]
                subprocess.run(cmd_fc, capture_output=True, check=True)  # noqa: S603
                staged_ok = target_bg.exists() and target_bg.stat().st_size > 0
            except Exception as fc_err:
                logger.warning(
                    "filter_complex concat failed (%s), falling back to loop copy",
                    fc_err,
                )

        # 3. Ultimate fallback: single stream loop or copy
        if not staged_ok:
            try:
                cmd_fallback = [
                    ffmpeg_bin,
                    "-y",
                    "-stream_loop",
                    "-1",
                    "-i",
                    str(bg_source),
                    "-t",
                    f"{duration_sec:.1f}",
                    "-c",
                    "copy",
                    str(target_bg),
                ]
                subprocess.run(cmd_fallback, capture_output=True, check=True)  # noqa: S603
            except Exception:
                shutil.copy2(bg_source, target_bg)

        return target_bg.name

    def _prepare_banner(
        self, banner_video: Path | str | None, public_dir: Path
    ) -> tuple[str | None, int | None, int | None, int | None]:
        """Stage optional promo banner and probe frame duration and dimensions."""
        if not banner_video:
            return None, None, None, None

        banner_path = Path(banner_video)
        if not banner_path.is_file():
            alt_path = self.config.banners_dir / banner_video
            if alt_path.is_file():
                banner_path = alt_path

        if not banner_path.is_file():
            logger.warning("Banner video '%s' not found, skipping banner", banner_video)
            return None, None, None, None

        banner_ext = banner_path.suffix.lower() or ".mp4"
        staged_banner_name = f"banner{banner_ext}"
        staged_banner_target = public_dir / staged_banner_name
        shutil.copy2(banner_path, staged_banner_target)

        banner_dur_frames = self._probe_video_duration_frames(
            banner_path, fps=self.config.fps
        )
        b_width, b_height = self._probe_video_dimensions(banner_path)
        return (
            staged_banner_name,
            banner_dur_frames,
            (b_width if b_width > 0 else None),
            (b_height if b_height > 0 else None),
        )

    def _prepare_music(
        self, background_music: Path | str | None, public_dir: Path
    ) -> str | None:
        """Stage optional background music file into public directory."""
        if not background_music:
            return None

        music_path = Path(background_music)
        if not music_path.is_file():
            alt_path = self.config.music_dir / background_music
            if alt_path.is_file():
                music_path = alt_path

        if not music_path.is_file():
            logger.warning("Background music '%s' not found, skipping music", background_music)
            return None

        music_ext = music_path.suffix.lower() or ".mp3"
        staged_music_name = f"music{music_ext}"
        staged_music_target = public_dir / staged_music_name
        shutil.copy2(music_path, staged_music_target)
        logger.info("Background music staged: %s", staged_music_name)
        return staged_music_name

    async def _prepare_challenge_images(
        self, challenge: QuizChallenge, workspace: QuizWorkspace, images_dir: Path
    ) -> None:
        """Download and stage visual trivia images concurrently for all questions."""
        image_tasks = []
        target_items = []
        for item in challenge.all_questions():
            has_local_file = False
            if item.local_image_path:
                p = Path(item.local_image_path)
                if p.exists() and p.is_file():
                    has_local_file = True

            if (item.image_url or item.image_query) and not has_local_file:
                dest = workspace.get_image_path(f"q_{item.question_number}.png")
                if item.image_url:
                    image_tasks.append(
                        self.script_service._download_and_verify_url(item.image_url, dest)
                    )
                else:
                    image_tasks.append(
                        self.image_service.search_and_download(item.image_query, dest)
                    )
                target_items.append(item)

        if image_tasks:
            results = await asyncio.gather(*image_tasks, return_exceptions=True)
            for item, res in zip(target_items, results, strict=False):
                if isinstance(res, Path) and res.exists():
                    item.local_image_path = str(res)
                else:
                    item.local_image_path = None

        for tier in challenge.tiers:
            for q in tier.questions:
                if q.local_image_path:
                    local_p = Path(q.local_image_path)
                    if not local_p.is_absolute():
                        if (images_dir / local_p.name).exists():
                            q.local_image_path = f"images/{local_p.name}"
                            continue
                        ws_candidate = workspace.get_image_path(local_p.name)
                        if ws_candidate.exists():
                            local_p = ws_candidate

                    if local_p.exists() and local_p.is_file():
                        target_img = images_dir / local_p.name
                        if not target_img.exists():
                            shutil.copy2(local_p, target_img)
                        q.local_image_path = f"images/{local_p.name}"
                    else:
                        target_img = images_dir / local_p.name
                        if target_img.exists():
                            q.local_image_path = f"images/{target_img.name}"
                        else:
                            logger.warning(
                                "Image file for question %d not found: %s",
                                q.question_number,
                                q.local_image_path,
                            )
                            q.local_image_path = None

    def _resolve_node_binary(self) -> str:
        """Locate the Node.js binary across system PATH and known Windows locations."""
        ensure_system_paths()
        node = shutil.which("node")
        if node:
            return node
        if sys.platform == "win32":
            known_win_paths = [
                Path("C:/Program Files/nodejs/node.exe"),
                Path("C:/Program Files (x86)/nodejs/node.exe"),
            ]
            for p in known_win_paths:
                if p.exists():
                    return str(p)
        return "node"

    def _build_remotion_command(
        self,
        props_path: Path,
        public_dir: Path,
        output_path: Path,
        profile: RenderProfile | None = None,
        composition_id: str = "QuizChallenge",
    ) -> list[str]:
        """Construct the Remotion CLI rendering command."""
        node_bin = self._resolve_node_binary()
        remotion_dir = self.config.remotion_dir.resolve()
        remotion_cli = (
            remotion_dir / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
        ).resolve()

        abs_output = output_path.resolve()
        abs_props = props_path.resolve()
        abs_public = public_dir.resolve()

        effective_profile = profile or self.config.render_profile

        # Dynamic concurrency: scaled to 75-80% CPU logical cores with RAM quota guard
        concurrency = calculate_optimal_concurrency(effective_profile)

        args = [
            "render",
            "src/index.ts",
            composition_id,
            str(abs_output),
            f"--props={abs_props}",
            f"--public-dir={abs_public}",
            f"--concurrency={concurrency}",
            f"--timeout={self.config.remotion_delay_render_timeout_ms}",
            f"--crf={self.config.crf}",
            f"--jpeg-quality={self.config.remotion_jpeg_quality}",
            f"--x264-preset={self.config.remotion_x264_preset}",
            "--pixel-format=yuv420p",
            "--overwrite",
        ]

        # In GPU_FAST profile, enable Chromium GPU ANGLE rasterization & bundle caching
        if effective_profile == RenderProfile.GPU_FAST:
            args.append(f"--gl={self.config.gl_backend}")
            if self.config.enable_bundle_cache:
                args.append("--bundle-cache")
        elif self.config.enable_bundle_cache:
            args.append("--bundle-cache")

        if remotion_cli.exists():
            return [node_bin, str(remotion_cli)] + args
        return ["npx", "remotion"] + args

    async def _render_remotion(
        self,
        props_path: Path,
        public_dir: Path,
        output_path: Path,
        progress_callback: Callable[[int, str], None] | None = None,
        profile: RenderProfile | None = None,
        composition_id: str = "QuizChallenge",
    ) -> None:
        """Execute Remotion CLI subprocess to render MP4 with real-time streaming."""
        ensure_system_paths()
        effective_profile = profile or self.config.render_profile
        cmd = self._build_remotion_command(
            props_path=props_path,
            public_dir=public_dir,
            output_path=output_path,
            profile=effective_profile,
            composition_id=composition_id,
        )

        caps = get_hardware_capabilities()
        env = os.environ.copy()
        if effective_profile == RenderProfile.GPU_FAST and caps.active_hw_encoder:
            env["VIDEOANALIZER_RENDER_PROFILE"] = "gpu_fast"
            env["VIDEOANALIZER_HW_ENCODER"] = caps.active_hw_encoder
        else:
            env["VIDEOANALIZER_RENDER_PROFILE"] = "cpu_safe"
            env.pop("VIDEOANALIZER_HW_ENCODER", None)

        async with get_render_semaphore():
            logger.info(
                "Executing Remotion render (profile=%s, hw_encoder=%s): %s",
                effective_profile,
                env.get("VIDEOANALIZER_HW_ENCODER", "libx264"),
                " ".join(cmd),
            )
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.config.remotion_dir.resolve()),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            collected_stdout: list[str] = []
            collected_stderr: list[str] = []

            async def read_stream(stream: asyncio.StreamReader, is_stderr: bool) -> None:
                while True:
                    line_b = await stream.readline()
                    if not line_b:
                        break
                    line = line_b.decode(errors="replace").strip()
                    if not line:
                        continue
                    if is_stderr:
                        collected_stderr.append(line)
                        logger.debug("[Remotion stderr] %s", line)
                    else:
                        collected_stdout.append(line)
                        kw_matches = ("rendered", "bundl", "encod", "compos")
                        if any(kw in line.lower() for kw in kw_matches):
                            logger.info("[Remotion] %s", line)
                        if progress_callback:
                            # 1. Bundling progress: 40% -> 46%
                            bundle_match = re.search(r"bundl\w*\s+.*?(\d+)%", line, re.IGNORECASE)
                            if bundle_match:
                                b_pct = int(bundle_match.group(1))
                                progress_callback(
                                    40 + int(b_pct * 0.06), f"Подготовка Remotion: {b_pct}%"
                                )
                            # 2. Rendering progress: 46% -> 90%
                            render_match = re.search(
                                r"rendered\s+(\d+)/(\d+)(?:,\s*time remaining:\s*([^,\n\r]+))?",
                                line,
                                re.IGNORECASE,
                            )
                            if render_match:
                                cur = int(render_match.group(1))
                                total = max(1, int(render_match.group(2)))
                                rem_time = render_match.group(3)
                                pct = 46 + int((cur / total) * 44)
                                time_str = f" (осталось {rem_time.strip()})" if rem_time else ""
                                frame_pct = int(cur / total * 100)
                                progress_callback(
                                    pct,
                                    f"Рендеринг видео: кадр {cur}/{total} ({frame_pct}%){time_str}",
                                )
                            # 3. Encoding progress: 90% -> 92%
                            encoded_match = re.search(r"encoded\s+(\d+)/(\d+)", line, re.IGNORECASE)
                            if encoded_match:
                                cur = int(encoded_match.group(1))
                                total = max(1, int(encoded_match.group(2)))
                                progress_callback(
                                    90 + int((cur / total) * 2),
                                    f"Кодирование видео: {cur}/{total} кадров",
                                )

            try:
                assert process.stdout is not None
                assert process.stderr is not None
                gather_coro = asyncio.gather(
                    read_stream(process.stdout, False),
                    read_stream(process.stderr, True),
                    process.wait(),
                )
                if self.config.render_timeout_sec and self.config.render_timeout_sec > 0:
                    await asyncio.wait_for(
                        gather_coro,
                        timeout=self.config.render_timeout_sec,
                    )
                else:
                    await gather_coro
            except TimeoutError as exc:
                process.kill()
                raise TimeoutError(
                    f"Remotion render timed out after {self.config.render_timeout_sec} seconds"
                ) from exc

        if process.returncode != 0:
            err_msg = "\n".join(collected_stderr[-30:])
            out_msg = "\n".join(collected_stdout[-30:])
            logger.error(
                "Remotion render failed with exit code %s: %s", process.returncode, err_msg
            )
            # Automatic fail-safe fallback to CPU Safe if GPU_FAST failed (Clarification 1)
            if effective_profile == RenderProfile.GPU_FAST:
                logger.warning(
                    "GPU Fast Remotion render failed (code %s). "
                    "Automatically falling back to CPU Safe profile...",
                    process.returncode,
                )
                if progress_callback:
                    progress_callback(42, "Откат на CPU Safe рендеринг...")
                return await self._render_remotion(
                    props_path=props_path,
                    public_dir=public_dir,
                    output_path=output_path,
                    progress_callback=progress_callback,
                    profile=RenderProfile.CPU_SAFE,
                )
            raise RuntimeError(
                f"Remotion render failed (code {process.returncode}):\n{err_msg}\n{out_msg}"
            )

        logger.info("Remotion render completed successfully: %s", output_path)

    async def generate(
        self,
        topic: str,
        language: str = "ru",
        background_video: Path | str | None = None,
        voice: str | None = None,
        output_filename: str | None = None,
        banner_video: Path | str | None = None,
        challenge: QuizChallenge | None = None,
        retention_config: QuizRetentionConfig | None = None,
        creative_temperature: float | None = None,
        fact_check: bool | None = None,
        intro_hook: str | None = None,
        background_music: Path | str | None = None,
        background_music_volume: float = 0.18,
        uniquifier: VideoUniquifierConfig | None = None,
        render_profile: RenderProfile | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
        voice_config: VoiceConfig | None = None,
        background_mode: str = "loop",
    ) -> Path:
        """Run the full end-to-end quiz short generation pipeline."""
        if progress_callback:
            progress_callback(10, "Инициализация генерации...")
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        bg_source = self.select_background(background_video)

        # Generate unique output path
        clean_topic = "".join(c if c.isalnum() else "_" for c in topic.strip()).strip("_")[:30]
        if not clean_topic:
            clean_topic = "quiz"
        timestamp_ms = int(asyncio.get_event_loop().time() * 1000)

        if output_filename:
            candidate = Path(output_filename)
            if candidate.is_absolute() or len(candidate.parts) > 1:
                final_output_path = candidate.resolve()
            else:
                final_output_path = (self.config.output_dir / candidate.name).resolve()
        else:
            final_output_path = (
                self.config.output_dir / f"{clean_topic}_{timestamp_ms}.mp4"
            ).resolve()

        if final_output_path.suffix.lower() != ".mp4":
            final_output_path = final_output_path.with_suffix(".mp4")
        final_output_path.parent.mkdir(parents=True, exist_ok=True)

        async with QuizWorkspace(base_dir=self.config.temp_dir) as workspace:
            logger.info("Started quiz generation in workspace %s", workspace.path)
            if progress_callback:
                progress_callback(15, "Подготовка звуковых эффектов и ассетов...")

            # 1. Create public directory structure inside workspace for Remotion serving
            public_dir = workspace.path / "public"
            audio_dir = public_dir / "audio"
            images_dir = public_dir / "images"
            sfx_target_dir = public_dir / "sfx"

            audio_dir.mkdir(parents=True, exist_ok=True)
            images_dir.mkdir(parents=True, exist_ok=True)
            sfx_target_dir.mkdir(parents=True, exist_ok=True)

            # 2. Stage SFX files into public/sfx
            raw_sfx = self.audio_service.ensure_default_sfx(self.config.sfx_dir)
            tick_src = Path(raw_sfx.timer_tick)
            staged_tick_name = f"timer_tick{tick_src.suffix}"
            shutil.copy2(tick_src, sfx_target_dir / staged_tick_name)
            shutil.copy2(raw_sfx.reveal_ding, sfx_target_dir / "reveal_ding.wav")
            shutil.copy2(raw_sfx.level_up, sfx_target_dir / "level_up.wav")

            heartbeat_panic_rel = None
            if raw_sfx.heartbeat_panic and Path(raw_sfx.heartbeat_panic).exists():
                shutil.copy2(raw_sfx.heartbeat_panic, sfx_target_dir / "heartbeat_panic.wav")
                heartbeat_panic_rel = "sfx/heartbeat_panic.wav"

            streak_fire_rel = None
            if raw_sfx.streak_fire and Path(raw_sfx.streak_fire).exists():
                shutil.copy2(raw_sfx.streak_fire, sfx_target_dir / "streak_fire.wav")
                streak_fire_rel = "sfx/streak_fire.wav"

            rank_levelup_rel = None
            if raw_sfx.rank_levelup and Path(raw_sfx.rank_levelup).exists():
                shutil.copy2(raw_sfx.rank_levelup, sfx_target_dir / "rank_levelup.wav")
                rank_levelup_rel = "sfx/rank_levelup.wav"

            comment_buzzer_rel = None
            if raw_sfx.comment_buzzer and Path(raw_sfx.comment_buzzer).exists():
                shutil.copy2(raw_sfx.comment_buzzer, sfx_target_dir / "comment_buzzer.wav")
                comment_buzzer_rel = "sfx/comment_buzzer.wav"

            staged_sfx = SfxPaths(
                timer_tick=f"sfx/{staged_tick_name}",
                reveal_ding="sfx/reveal_ding.wav",
                level_up="sfx/level_up.wav",
                heartbeat_panic=heartbeat_panic_rel,
                streak_fire=streak_fire_rel,
                rank_levelup=rank_levelup_rel,
                comment_buzzer=comment_buzzer_rel,
            )


            # 3. Generate structured 9-question challenge if not already provided
            if challenge is None:
                if progress_callback:
                    progress_callback(20, "Генерация 9 вопросов квиза...")
                logger.info("Generating 9-question quiz challenge for topic: %s", topic)
                challenge = await self.script_service.generate_quiz(
                    topic=topic,
                    language=language,
                    workspace=workspace,
                    creative_temperature=creative_temperature,
                    fact_check=fact_check,
                )
            else:
                logger.info(
                    "Using pre-approved quiz challenge with %d questions for topic: %s",
                    len(challenge.all_questions()),
                    topic,
                )

            # 4. Concurrent Data Pipeline: Parallelize TTS, images, and media assets
            if progress_callback:
                progress_callback(25, "Параллельная подготовка аудио и медиа-ассетов...")

            target_bg = public_dir / "background.mp4"

            task_audio = self.audio_service.synthesize_cue_sheet(
                challenge=challenge,
                output_dir=audio_dir,
                voice=voice,
                retention_config=retention_config,
                intro_hook=intro_hook,
                voice_config=voice_config,
            )
            task_images = self._prepare_challenge_images(
                challenge=challenge,
                workspace=workspace,
                images_dir=images_dir,
            )
            task_bg = asyncio.to_thread(
                self._prepare_background,
                bg_source,
                target_bg,
                120.0,
                background_mode,
                background_video,
            )
            task_banner = asyncio.to_thread(self._prepare_banner, banner_video, public_dir)
            task_music = asyncio.to_thread(self._prepare_music, background_music, public_dir)

            logger.info("Awaiting concurrent completion of TTS and media assets")
            (
                cue_sheet,
                _,
                staged_bg_name,
                (staged_banner_name, banner_dur_frames, banner_width, banner_height),
                staged_music_name,
            ) = await asyncio.gather(
                task_audio,
                task_images,
                task_bg,
                task_banner,
                task_music,
            )

            # 5. Normalize cue audio file paths relative to public dir (e.g. "audio/...")
            if cue_sheet.intro_hook_audio_file:
                cue_sheet.intro_hook_audio_file = (
                    f"audio/{Path(cue_sheet.intro_hook_audio_file).name}"
                )
            for cue in cue_sheet.cues:
                if cue.question_audio_file:
                    cue.question_audio_file = f"audio/{Path(cue.question_audio_file).name}"
                if cue.answer_audio_file:
                    cue.answer_audio_file = f"audio/{Path(cue.answer_audio_file).name}"

            # 6. Apply promo banner temporal offset to cue sheet if staged
            banner_start_frame: int | None = None
            banner_duration_frames: int | None = None
            if staged_banner_name and banner_dur_frames:
                total_frames = cue_sheet.total_duration_frames
                banner_duration_frames = min(banner_dur_frames, total_frames)
                insert_idx = (
                    4 if len(cue_sheet.cues) >= 5 else max(1, len(cue_sheet.cues) // 2)
                )
                banner_start_frame = cue_sheet.cues[insert_idx - 1].end_frame

                for cue in cue_sheet.cues[insert_idx:]:
                    cue.start_frame += banner_duration_frames
                    cue.think_start_frame += banner_duration_frames
                    cue.reveal_frame += banner_duration_frames
                    cue.end_frame += banner_duration_frames

                cue_sheet.total_duration_frames += banner_duration_frames
                cue_sheet.total_duration_ms += int(
                    banner_duration_frames * 1000 / self.config.fps
                )
                logger.info(
                    "Promo banner integrated into timeline: name=%s, dur_frames=%d, start_frame=%d",
                    staged_banner_name,
                    banner_duration_frames,
                    banner_start_frame,
                )

            # 7. Assemble RemotionRenderProps
            remotion_props = RemotionRenderProps(
                challenge=challenge,
                cue_sheet=cue_sheet,
                background_video_path=staged_bg_name,
                sfx_paths=staged_sfx,
                retention=retention_config or QuizRetentionConfig(),
                fps=self.config.fps,
                width=self.config.width,
                height=self.config.height,
                banner_video_path=staged_banner_name,
                banner_start_frame=banner_start_frame,
                banner_duration_frames=banner_duration_frames,
                banner_width=banner_width,
                banner_height=banner_height,
                background_music_path=staged_music_name,
                background_music_volume=background_music_volume,
            )

            props_file = workspace.path / "remotion-props.json"
            props_file.write_text(
                remotion_props.model_dump_json(indent=2),
                encoding="utf-8",
            )

            # 8. Execute Remotion CLI render
            if progress_callback:
                progress_callback(40, "Запуск рендеринга Remotion...")
            logger.info("Rendering final vertical video to %s", final_output_path)
            await self._render_remotion(
                props_path=props_file,
                public_dir=public_dir,
                output_path=final_output_path,
                progress_callback=progress_callback,
                profile=render_profile,
            )

        if not final_output_path.exists() or final_output_path.stat().st_size == 0:
            raise RuntimeError(
                f"Output video file was not generated or is empty: {final_output_path}"
            )

        # 9. Apply Video Uniquifier post-processing if enabled, or ensure 100% sterile metadata
        if uniquifier and uniquifier.enabled:
            if progress_callback:
                progress_callback(93, "Уникализация видео (Anti-Content ID)...")
            logger.info("Applying Video Uniquifier post-processing on %s", final_output_path)
            apply_video_uniquifier(
                input_path=final_output_path,
                output_path=final_output_path,
                config=uniquifier,
                width=self.config.width,
                height=self.config.height,
                render_profile=render_profile or self.config.render_profile,
            )
        else:
            from videoanalizer.media.uniquifier import strip_video_metadata

            logger.info("Purging Remotion container metadata from %s", final_output_path)
            strip_video_metadata(final_output_path, final_output_path)

        if progress_callback:
            progress_callback(100, "Видео успешно создано!")

        logger.info(
            "Quiz shorts video ready: %s (size: %d bytes)",
            final_output_path,
            final_output_path.stat().st_size,
        )
        return final_output_path

    async def render_visual_quiz(
        self,
        dataset: VisualQuizDataset,
        output_path: Path | str | None = None,
        background_video: Path | str | None = None,
        background_music: Path | str | None = None,
        background_music_volume: float = 0.18,
        voice: str | None = None,
        voice_config: VoiceConfig | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
        render_profile: RenderProfile | None = None,
        background_mode: str = "loop",
    ) -> Path:
        """Render VisualImageQuiz dataset into 1080x1920 60fps MP4 video via Remotion."""
        ensure_system_paths()
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        final_output = (
            Path(output_path)
            if output_path
            else self.config.output_dir / f"visual_quiz_{timestamp}_{secrets.token_hex(3)}.mp4"
        )
        final_output.parent.mkdir(parents=True, exist_ok=True)

        async with get_render_semaphore():
            with QuizWorkspace(base_dir=self.config.temp_dir) as ws:
                public_dir = ws.public_dir
                public_dir.mkdir(parents=True, exist_ok=True)

                if progress_callback:
                    progress_callback(5, "Подготовка фонового видео...")

                # 1. Background video
                bg_source = self.select_background(background_video)
                target_bg = public_dir / "background.mp4"
                await asyncio.to_thread(
                    self._prepare_background,
                    bg_source,
                    target_bg,
                    120.0,
                    background_mode,
                    background_video,
                )

                # 2. Stage images into public/images/
                images_dir = public_dir / "images"
                images_dir.mkdir(parents=True, exist_ok=True)
                for item in dataset.items:
                    img_filename = f"item_{item.id}.png"
                    dest_img_path = images_dir / img_filename
                    if item.image_path and Path(item.image_path).exists():
                        shutil.copy2(item.image_path, dest_img_path)
                        item.image_path = f"images/{img_filename}"
                    elif item.image_url:
                        downloaded = await self.image_service.search_and_download(item.image_query, dest_img_path)
                        if downloaded:
                            item.image_path = f"images/{img_filename}"
                        else:
                            item.image_path = None
                    else:
                        item.image_path = None

                if progress_callback:
                    progress_callback(20, "Синтез дикторской речи и звуковых эффектов...")

                # 3. Audio synthesis
                (
                    master_audio_path,
                    timing_slots,
                    subtitles,
                    total_duration_frames,
                    hook_end_frame,
                ) = await self.audio_service.generate_visual_quiz_audio(
                    dataset=dataset,
                    workspace=ws,
                    voice=voice,
                    voice_config=voice_config,
                )

                public_audio = public_dir / "audio" / "visual_quiz_master_mix.wav"
                public_audio.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(master_audio_path, public_audio)

                # 4. Prepare Remotion props
                props = VisualQuizRenderProps(
                    dataset=dataset,
                    fps=self.config.fps,
                    width=1080,
                    height=1920,
                    total_duration_frames=total_duration_frames,
                    hook_end_frame=hook_end_frame,
                    timing_slots=timing_slots,
                    subtitles=subtitles,
                    audio_mix_path="audio/visual_quiz_master_mix.wav",
                    background_video_path="background.mp4",
                )

                props_file = ws.path / "remotion-props.json"
                props_file.write_text(props.model_dump_json(indent=2), encoding="utf-8")

                if progress_callback:
                    progress_callback(40, "Рендер видео через Remotion 60fps...")

                # 5. Render Remotion
                await self._render_remotion(
                    props_path=props_file,
                    public_dir=public_dir,
                    output_path=final_output,
                    progress_callback=progress_callback,
                    profile=render_profile or self.config.render_profile,
                    composition_id="VisualImageQuiz",
                )

                # 6. Metadata cleanup
                from videoanalizer.media.uniquifier import strip_video_metadata
                strip_video_metadata(final_output, final_output)

                if progress_callback:
                    progress_callback(100, "Видео успешно создано!")

                logger.info("VisualImageQuiz rendered successfully to %s", final_output)
                return final_output


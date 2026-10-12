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

from videoanalizer.media.uniquifier import VideoUniquifierConfig, apply_video_uniquifier
from videoanalizer.quiz.audio_service import AudioService
from videoanalizer.quiz.config import QuizConfig, ensure_system_paths, get_quiz_config
from videoanalizer.quiz.image_service import ImageService
from videoanalizer.quiz.models import (
    AudioCueSheet,
    QuizChallenge,
    QuizRetentionConfig,
    RemotionRenderProps,
    SfxPaths,
)
from videoanalizer.quiz.script_service import ScriptService
from videoanalizer.quiz.workspace import QuizWorkspace

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

    def __init__(self, config: QuizConfig | None = None) -> None:
        self.config = config or get_quiz_config()
        self.script_service = ScriptService(config=self.config)
        self.audio_service = AudioService(config=self.config)
        self.image_service = ImageService()

    def select_background(self, explicit_path: Path | str | None = None) -> Path:
        """Select a vertical background video, either specific or randomly chosen."""
        if explicit_path and str(explicit_path).strip().lower() != "random":
            p = Path(explicit_path)
            if p.exists() and p.is_file():
                return p
            p_in_bg = self.config.backgrounds_dir / explicit_path
            if p_in_bg.exists() and p_in_bg.is_file():
                return p_in_bg
            logger.warning(
                "Explicit background '%s' not found, falling back to random background",
                explicit_path,
            )

        bg_dir = self.config.backgrounds_dir
        if bg_dir.exists():
            mp4_candidates = [
                f for f in bg_dir.glob("*.mp4")
                if not f.name.startswith(".")
            ]
            if mp4_candidates:
                return secrets.choice(mp4_candidates)

        default_bg = bg_dir / "default_bg.mp4"
        if default_bg.exists():
            return default_bg

        raise FileNotFoundError(
            f"No background videos found in {bg_dir}. "
            f"Please place a 9:16 background video in {bg_dir}."
        )

    def _probe_video_duration_frames(self, video_path: Path, fps: int = 60) -> int:
        """Probe video duration and calculate duration in frames."""
        ensure_system_paths()
        ffprobe_bin = shutil.which("ffprobe")
        if not ffprobe_bin:
            return fps * 5
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
            dur_sec = float(data["format"]["duration"])
            return max(1, int(dur_sec * fps))
        except Exception as exc:
            logger.warning("Could not probe video duration for %s: %s", video_path, exc)
            return fps * 5

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

        # Dynamic concurrency based on available CPU cores
        cpu_count = os.cpu_count() or 4
        concurrency = min(6, max(2, cpu_count // 2 if cpu_count >= 6 else cpu_count - 1))

        args = [
            "render",
            "src/index.ts",
            "QuizChallenge",
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

        if remotion_cli.exists():
            return [node_bin, str(remotion_cli)] + args
        return ["npx", "remotion"] + args

    async def _render_remotion(
        self,
        props_path: Path,
        public_dir: Path,
        output_path: Path,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> None:
        """Execute Remotion CLI subprocess to render MP4 with real-time streaming."""
        ensure_system_paths()
        cmd = self._build_remotion_command(
            props_path=props_path,
            public_dir=public_dir,
            output_path=output_path,
        )

        async with get_render_semaphore():
            logger.info("Executing Remotion render: %s", " ".join(cmd))
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.config.remotion_dir.resolve()),
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
        intro_hook: str | None = "Ты гений, если ответишь на все вопросы!",
        background_music: Path | str | None = None,
        background_music_volume: float = 0.18,
        uniquifier: VideoUniquifierConfig | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
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


            # 3. Generate structured 9-question challenge or use pre-approved challenge
            if progress_callback:
                progress_callback(20, "Подготовка вопросов и визуальных подсказок...")
            if challenge is not None:
                logger.info(
                    "Using pre-approved quiz challenge with %d questions for topic: %s",
                    len(challenge.all_questions()),
                    topic,
                )
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
            else:
                logger.info("Generating 9-question quiz challenge for topic: %s", topic)
                challenge = await self.script_service.generate_quiz(
                    topic=topic,
                    language=language,
                    workspace=workspace,
                    creative_temperature=creative_temperature,
                    fact_check=fact_check,
                )

            # Ensure image paths in challenge are staged and relative to public directory
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
                            # Relative path within public dir e.g. "images/q1.jpg"
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

            # 4. Synthesize synchronized voiceovers and word boundary cue sheet
            if progress_callback:
                progress_callback(30, "Синтез речи нейросетью Edge-TTS...")
            logger.info("Synthesizing audio narration and karaoke cues")
            cue_sheet: AudioCueSheet = await self.audio_service.synthesize_cue_sheet(
                challenge=challenge,
                output_dir=audio_dir,
                voice=voice,
                retention_config=retention_config,
                intro_hook=intro_hook,
            )

            # Normalize cue audio file paths to be relative to public dir (e.g. "audio/...")
            if cue_sheet.intro_hook_audio_file:
                cue_sheet.intro_hook_audio_file = (
                    f"audio/{Path(cue_sheet.intro_hook_audio_file).name}"
                )
            for cue in cue_sheet.cues:
                if cue.question_audio_file:
                    cue.question_audio_file = f"audio/{Path(cue.question_audio_file).name}"
                if cue.answer_audio_file:
                    cue.answer_audio_file = f"audio/{Path(cue.answer_audio_file).name}"

            # 5. Stage Background Video into public/background.mp4 with continuous duration loop
            if progress_callback:
                progress_callback(38, "Подготовка фонового видеоряда...")
            staged_bg_name = "background.mp4"
            target_bg = public_dir / staged_bg_name
            target_duration_sec = (cue_sheet.total_duration_ms / 1000.0) + 15.0

            ensure_system_paths()
            ffmpeg_bin = shutil.which("ffmpeg")
            looped = False
            if ffmpeg_bin:
                try:
                    cmd_loop = [
                        ffmpeg_bin,
                        "-y",
                        "-stream_loop",
                        "-1",
                        "-i",
                        str(bg_source),
                        "-t",
                        f"{target_duration_sec:.1f}",
                        "-c",
                        "copy",
                        str(target_bg),
                    ]
                    subprocess.run(cmd_loop, capture_output=True, check=True)  # noqa: S603
                    looped = True
                except Exception as loop_err:
                    logger.warning(
                        "FFmpeg stream loop failed (%s), falling back to copy", loop_err
                    )

            if not looped:
                shutil.copy2(bg_source, target_bg)

            # 6. Optional promo banner staging & temporal center positioning
            staged_banner_name: str | None = None
            banner_start_frame: int | None = None
            banner_duration_frames: int | None = None

            if banner_video:
                banner_path = Path(banner_video)
                if not banner_path.is_file():
                    alt_path = self.config.banners_dir / banner_video
                    if alt_path.is_file():
                        banner_path = alt_path

                if banner_path.is_file():
                    banner_ext = banner_path.suffix.lower() or ".mp4"
                    staged_banner_name = f"banner{banner_ext}"
                    staged_banner_target = public_dir / staged_banner_name
                    shutil.copy2(banner_path, staged_banner_target)

                    banner_dur_frames = self._probe_video_duration_frames(
                        banner_path, fps=self.config.fps
                    )
                    total_frames = cue_sheet.total_duration_frames
                    banner_duration_frames = min(banner_dur_frames, total_frames)

                    # Insert promo banner midway between Level 1 and Level 2 (after Question 4)
                    insert_idx = (
                        4 if len(cue_sheet.cues) >= 5 else max(1, len(cue_sheet.cues) // 2)
                    )
                    banner_start_frame = cue_sheet.cues[insert_idx - 1].end_frame

                    # Shift all subsequent question cues so quiz pauses completely during banner
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
                        "Promo banner staged: name=%s, dur_frames=%d, start_frame=%d (total=%d)",
                        staged_banner_name,
                        banner_duration_frames,
                        banner_start_frame,
                        cue_sheet.total_duration_frames,
                    )
                else:
                    logger.warning(
                        "Banner video '%s' not found, skipping banner", banner_video
                    )

            # 7. Optional background music staging
            staged_music_name: str | None = None
            if background_music:
                music_path = Path(background_music)
                if not music_path.is_file():
                    alt_path = self.config.music_dir / background_music
                    if alt_path.is_file():
                        music_path = alt_path

                if music_path.is_file():
                    music_ext = music_path.suffix.lower() or ".mp3"
                    staged_music_name = f"music{music_ext}"
                    staged_music_target = public_dir / staged_music_name
                    shutil.copy2(music_path, staged_music_target)
                    logger.info("Background music staged: %s", staged_music_name)
                else:
                    logger.warning(
                        "Background music '%s' not found, skipping music", background_music
                    )

            # 8. Assemble RemotionRenderProps
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
                background_music_path=staged_music_name,
                background_music_volume=background_music_volume,
            )


            props_file = workspace.path / "remotion-props.json"
            props_file.write_text(
                remotion_props.model_dump_json(indent=2),
                encoding="utf-8",
            )

            # 7. Execute Remotion CLI render
            if progress_callback:
                progress_callback(40, "Запуск рендеринга Remotion...")
            logger.info("Rendering final vertical video to %s", final_output_path)
            if progress_callback is not None:
                await self._render_remotion(
                    props_path=props_file,
                    public_dir=public_dir,
                    output_path=final_output_path,
                    progress_callback=progress_callback,
                )
            else:
                await self._render_remotion(
                    props_path=props_file,
                    public_dir=public_dir,
                    output_path=final_output_path,
                )

        if not final_output_path.exists() or final_output_path.stat().st_size == 0:
            raise RuntimeError(
                f"Output video file was not generated or is empty: {final_output_path}"
            )

        # 9. Apply Video Uniquifier post-processing if enabled
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
            )

        if progress_callback:
            progress_callback(100, "Видео успешно создано!")

        logger.info(
            "Quiz shorts video ready: %s (size: %d bytes)",
            final_output_path,
            final_output_path.stat().st_size,
        )
        return final_output_path

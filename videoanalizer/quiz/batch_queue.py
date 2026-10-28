"""BatchQueueManager: Progressive script generation, sequential rendering, and history."""

import asyncio
import io
import json
import logging
import re
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from videoanalizer.quiz.config import QuizConfig, get_quiz_config
from videoanalizer.quiz.models import (
    BatchQueueItem,
    BatchQueueItemStatus,
    BatchQueueState,
    BatchRenderStartRequest,
    GenerationHistoryItem,
    QuizChallenge,
    QuizRetentionConfig,
)
from videoanalizer.quiz.orchestrator import QuizOrchestrator
from videoanalizer.quiz.rate_limiter import get_gemini_rate_limiter

logger = logging.getLogger(__name__)


class BatchQueueManager:
    """Singleton queue manager managing multi-video batches, 15 RPM progressive generation,

    hardware-safe Remotion sequential rendering (asyncio.Semaphore(1)), and persistent history.
    """

    def __init__(self, config: QuizConfig | None = None) -> None:
        self.config = config or get_quiz_config()
        self.orchestrator = QuizOrchestrator(config=self.config)
        self.render_semaphore = asyncio.Semaphore(1)

        self.current_state: BatchQueueState | None = None
        self._generator_task: asyncio.Task | None = None
        self._render_worker_task: asyncio.Task | None = None
        self._history_file = self.config.output_dir / "generation_history.json"
        self._lock = asyncio.Lock()

    @staticmethod
    def _clean_topic_from_stem(stem: str) -> str:
        """Derive human-readable topic title from MP4 filename stem."""
        clean = re.sub(r"_\d{6,}$", "", stem)
        clean = clean.replace("_", " ").strip()
        return clean or stem

    def get_history(self) -> list[GenerationHistoryItem]:
        """Load recorded video creations from history file and disk."""
        items_by_path: dict[str, GenerationHistoryItem] = {}

        # 1. Load recorded entries from history file if exists
        if self._history_file.exists():
            try:
                raw = self._history_file.read_text(encoding="utf-8")
                data = json.loads(raw)
                for entry in data:
                    item = GenerationHistoryItem.model_validate(entry)
                    if Path(item.video_path).exists():
                        norm_p = str(Path(item.video_path).resolve())
                        if norm_p not in items_by_path:
                            items_by_path[norm_p] = item
            except Exception as exc:
                logger.warning("Failed to load generation history: %s", exc)

        # 2. Auto-discover MP4 videos in output directory that may not be indexed yet
        candidate_dirs = [self.config.output_dir]
        if self._history_file == self.config.output_dir / "generation_history.json":
            for fallback in (Path("output"), Path("outputs")):
                if fallback.resolve() != self.config.output_dir.resolve():
                    candidate_dirs.append(fallback)

        seen_dirs: set[Path] = set()
        for d in candidate_dirs:
            p_dir = Path(d).resolve()
            if p_dir in seen_dirs or not p_dir.exists():
                continue
            seen_dirs.add(p_dir)
            for mp4 in p_dir.glob("*.mp4"):
                norm_p = str(mp4.resolve())
                if norm_p not in items_by_path:
                    try:
                        mtime = mp4.stat().st_mtime
                        created_dt = datetime.fromtimestamp(mtime, tz=UTC)
                    except OSError:
                        created_dt = datetime.now(UTC)
                    topic = self._clean_topic_from_stem(mp4.stem)
                    gh_item = GenerationHistoryItem(
                        history_id=f"gh_{mp4.stem}",
                        job_id=mp4.stem,
                        topic=topic,
                        created_at=created_dt,
                        video_path=norm_p,
                        download_url=f"/api/v1/quiz/history/download/{mp4.stem}",
                        duration_seconds=60.0,
                    )
                    items_by_path[norm_p] = gh_item

        result = list(items_by_path.values())
        result.sort(key=lambda x: x.created_at, reverse=True)
        result = result[:100]

        # 3. Cache auto-discovered items if history file does not exist yet
        if result and not self._history_file.exists():
            try:
                self._history_file.parent.mkdir(parents=True, exist_ok=True)
                serialized = [it.model_dump(mode="json") for it in result]
                self._history_file.write_text(
                    json.dumps(serialized, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            except Exception as exc:
                logger.debug("Failed to cache initial history: %s", exc)

        return result

    def record_history(self, item: BatchQueueItem) -> None:
        """Append a completed video to persistent generation history."""
        if not item.video_path or not Path(item.video_path).exists():
            return

        history_list = self.get_history()
        gh_item = GenerationHistoryItem(
            history_id=f"gh_{uuid.uuid4().hex[:10]}",
            job_id=item.item_id,
            topic=item.topic,
            created_at=datetime.now(UTC),
            video_path=item.video_path,
            download_url=item.download_url or f"/api/v1/quiz/history/download/{item.item_id}",
            duration_seconds=60.0,
        )

        norm_target = str(Path(item.video_path).resolve())
        history_list = [
            it for it in history_list
            if str(Path(it.video_path).resolve()) != norm_target
        ]
        history_list.insert(0, gh_item)

        # Keep last 50 entries
        history_list = history_list[:50]

        try:
            self._history_file.parent.mkdir(parents=True, exist_ok=True)
            serialized = [it.model_dump(mode="json") for it in history_list]
            self._history_file.write_text(
                json.dumps(serialized, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.info("Recorded history item for topic '%s' (%s)", item.topic, gh_item.history_id)
        except Exception as exc:
            logger.warning("Failed to save generation history: %s", exc)

    async def init_batch(
        self,
        topics: list[str],
        language: str = "ru",
        temperature: float | None = None,
        fact_check: bool | None = None,
    ) -> BatchQueueState:
        """Initialize a new batch session and launch progressive background generation."""
        async with self._lock:
            # Cancel any running background generator
            if self._generator_task and not self._generator_task.done():
                self._generator_task.cancel()

            batch_id = f"bq_{uuid.uuid4().hex[:10]}"
            items: list[BatchQueueItem] = []

            for idx, topic in enumerate(topics, 1):
                clean_topic = topic.strip()
                if not clean_topic:
                    continue
                items.append(
                    BatchQueueItem(
                        item_id=f"bqi_{uuid.uuid4().hex[:10]}",
                        index=idx,
                        topic=clean_topic,
                        challenge=None,
                        status=BatchQueueItemStatus.PENDING_GENERATION,
                        progress_percent=0,
                        stage="Ожидает генерации сценария...",
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                    )
                )

            self.current_state = BatchQueueState(
                batch_id=batch_id,
                items=items,
                is_rendering=False,
                active_item_id=None,
                completed_count=0,
                total_count=len(items),
                rate_limit_waiting=False,
                rate_limit_delay_sec=0.0,
            )

            # Spawn progressive generator task
            self._generator_task = asyncio.create_task(
                self._progressive_script_generator_loop(
                    batch_id=batch_id,
                    language=language,
                    temperature=temperature,
                    fact_check=fact_check,
                )
            )

            return self.current_state

    async def _progressive_script_generator_loop(
        self,
        batch_id: str,
        language: str,
        temperature: float | None,
        fact_check: bool | None,
    ) -> None:
        """Paced generation of scripts for all items in batch respecting 15 RPM limit."""
        if not self.current_state or self.current_state.batch_id != batch_id:
            return

        limiter = get_gemini_rate_limiter()

        for item in self.current_state.items:
            if item.status != BatchQueueItemStatus.PENDING_GENERATION:
                continue

            try:
                rem_wait = limiter.get_remaining_wait()
                if rem_wait > 0.5:
                    self.current_state.rate_limit_waiting = True
                    self.current_state.rate_limit_delay_sec = round(rem_wait, 1)
                    item.stage = f"Соблюдение квоты ИИ (ожидание {round(rem_wait, 1)}с)..."

                item.stage = "Генерация 9 вопросов ИИ..."
                challenge = await self.orchestrator.script_service.generate_quiz(
                    topic=item.topic,
                    language=language,
                    creative_temperature=temperature,
                    fact_check=fact_check,
                )

                item.challenge = challenge
                item.status = BatchQueueItemStatus.PENDING_APPROVAL
                item.stage = "Вопросы готовы к проверке"
                item.progress_percent = 100
                item.updated_at = datetime.now(UTC)
                logger.info(
                    "Progressive generation completed for batch item %d/%d ('%s')",
                    item.index,
                    len(self.current_state.items),
                    item.topic,
                )
            except Exception as exc:
                logger.error("Failed to generate script for item %s: %s", item.item_id, exc)
                item.status = BatchQueueItemStatus.FAILED
                item.error_message = str(exc)
                item.stage = f"Ошибка генерации: {exc}"
            finally:
                if self.current_state:
                    self.current_state.rate_limit_waiting = False
                    self.current_state.rate_limit_delay_sec = 0.0

    def update_item_challenge(self, item_id: str, challenge: QuizChallenge) -> bool:
        """Update approved challenge for a specific item during user review."""
        if not self.current_state:
            return False
        for it in self.current_state.items:
            if it.item_id == item_id:
                it.challenge = challenge
                it.updated_at = datetime.now(UTC)
                return True
        return False

    def remove_item(self, item_id: str) -> bool:
        """Remove or skip an item from the batch during review."""
        if not self.current_state:
            return False
        orig_len = len(self.current_state.items)
        self.current_state.items = [it for it in self.current_state.items if it.item_id != item_id]
        if len(self.current_state.items) != orig_len:
            # Reindex
            for idx, it in enumerate(self.current_state.items, 1):
                it.index = idx
            self.current_state.total_count = len(self.current_state.items)
            return True
        return False

    async def start_render_queue(self, request: BatchRenderStartRequest) -> BatchQueueState:
        """Enqueue approved batch items into sequential Remotion rendering queue."""
        async with self._lock:
            if not self.current_state or self.current_state.batch_id != request.batch_id:
                # Re-create state from request if session was restarted
                self.current_state = BatchQueueState(
                    batch_id=request.batch_id,
                    items=request.items,
                    is_rendering=False,
                    active_item_id=None,
                    completed_count=0,
                    total_count=len(request.items),
                )

            # Update existing items with request updates (approved challenges)
            req_item_map = {it.item_id: it for it in request.items}
            for it in self.current_state.items:
                if it.item_id in req_item_map:
                    req_it = req_item_map[it.item_id]
                    if req_it.challenge:
                        it.challenge = req_it.challenge
                if it.status in (
                    BatchQueueItemStatus.PENDING_APPROVAL,
                    BatchQueueItemStatus.PENDING_GENERATION,
                ):
                    it.status = BatchQueueItemStatus.QUEUED
                    it.stage = "В очереди на рендеринг"
                    it.progress_percent = 0

            # Start worker if not already running
            if not self._render_worker_task or self._render_worker_task.done():
                self._render_worker_task = asyncio.create_task(self._render_worker_loop(request))

            return self.current_state

    async def _render_worker_loop(self, request: BatchRenderStartRequest) -> None:
        """FIFO Sequential Remotion Render worker with concurrency = 1 (Semaphore=1)."""
        logger.info("Batch render worker started for batch '%s'", request.batch_id)
        used_batch_backgrounds: list[Path] = []

        while True:
            if not self.current_state:
                break

            # Find next item in QUEUED state
            next_item: BatchQueueItem | None = None
            for it in self.current_state.items:
                if it.status == BatchQueueItemStatus.QUEUED:
                    next_item = it
                    break

            if next_item is None:
                # No more queued items
                self.current_state.is_rendering = False
                self.current_state.active_item_id = None
                logger.info("Batch render queue completed for batch '%s'", request.batch_id)
                break

            self.current_state.is_rendering = True
            self.current_state.active_item_id = next_item.item_id
            next_item.status = BatchQueueItemStatus.RENDERING
            next_item.progress_percent = 10
            next_item.stage = "Запуск Remotion рендерера..."
            next_item.updated_at = datetime.now(UTC)

            logger.info(
                "📦 [Batch] Starting render for item %d/%d: '%s' (item_id=%s)",
                self.current_state.completed_count + 1,
                len(self.current_state.items),
                next_item.topic,
                next_item.item_id,
            )
            # Process under Semaphore(1) lock
            target_item = next_item
            async with self.render_semaphore:
                try:

                    def on_progress(
                        pct: int, stage_name: str, item: BatchQueueItem = target_item
                    ) -> None:
                        item.progress_percent = max(10, min(100, pct))
                        item.stage = stage_name

                    retention_cfg = QuizRetentionConfig(
                        enabled=request.retention_enabled,
                        rank_bar_enabled=request.rank_bar_enabled,
                        stress_timer_enabled=request.stress_timer_enabled,
                    )

                    # Dynamic background per video if "random" without repetition
                    if not request.background_video or request.background_video.lower() == "random":
                        bg_video = self.orchestrator.select_background(
                            "random", exclude_paths=used_batch_backgrounds
                        )
                        if isinstance(bg_video, Path):
                            used_batch_backgrounds.append(bg_video)
                    else:
                        bg_video = request.background_video

                    output_path = await self.orchestrator.generate(
                        topic=next_item.topic,
                        language="ru",
                        background_video=bg_video,
                        voice=request.voice,
                        banner_video=request.banner_video,
                        challenge=next_item.challenge,
                        retention_config=retention_cfg,
                        background_music=request.background_music,
                        background_music_volume=request.background_music_volume,
                        uniquifier=request.uniquifier,
                        render_profile=request.render_profile,
                        progress_callback=on_progress,
                        voice_config=request.voice_config,
                        intro_hook=request.intro_hook,
                    )

                    next_item.status = BatchQueueItemStatus.COMPLETED
                    next_item.progress_percent = 100
                    next_item.stage = "Видео готово!"
                    next_item.video_path = str(output_path)
                    next_item.download_url = f"/api/v1/quiz/batch/download/{next_item.item_id}"
                    next_item.updated_at = datetime.now(UTC)

                    self.current_state.completed_count += 1
                    self.record_history(next_item)
                    file_size_mb = output_path.stat().st_size / (1024 * 1024) if output_path.exists() else 0
                    logger.info(
                        "🎉 [Batch] Item %d/%d '%s' COMPLETED -> %s (%.1f MB)",
                        self.current_state.completed_count,
                        len(self.current_state.items),
                        next_item.topic,
                        output_path,
                        file_size_mb,
                    )

                except Exception as exc:
                    logger.error(
                        "Error rendering batch item %s ('%s'): %s",
                        next_item.item_id,
                        next_item.topic,
                        exc,
                        exc_info=True,
                    )
                    next_item.status = BatchQueueItemStatus.FAILED
                    next_item.error_message = str(exc)
                    next_item.stage = f"Ошибка рендеринга: {exc}"
                    next_item.updated_at = datetime.now(UTC)

            # Small pause between Remotion jobs to allow GPU memory deallocation
            await asyncio.sleep(2.0)

    def cancel_item(self, item_id: str) -> bool:
        """Cancel a queued item before it starts rendering."""
        if not self.current_state:
            return False
        for it in self.current_state.items:
            if it.item_id == item_id and it.status == BatchQueueItemStatus.QUEUED:
                it.status = BatchQueueItemStatus.CANCELLED
                it.stage = "Отменено пользователем"
                return True
        return False

    def clear_completed(self) -> None:
        """Remove completed and failed items from queue list."""
        if not self.current_state:
            return
        self.current_state.items = [
            it
            for it in self.current_state.items
            if it.status in (BatchQueueItemStatus.QUEUED, BatchQueueItemStatus.RENDERING)
        ]
        self.current_state.total_count = len(self.current_state.items)

    def create_batch_zip(self) -> io.BytesIO | None:
        """Package all completed MP4 files into a single in-memory ZIP archive."""
        if not self.current_state:
            return None

        completed_items = [
            it
            for it in self.current_state.items
            if it.status == BatchQueueItemStatus.COMPLETED
            and it.video_path
            and Path(it.video_path).exists()
        ]
        if not completed_items:
            return None

        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for it in completed_items:
                p = Path(it.video_path)
                arcname = f"{it.index:02d}_{it.topic.replace(' ', '_')[:30]}.mp4"
                zf.write(p, arcname=arcname)

        mem_zip.seek(0)
        return mem_zip


_global_batch_queue_manager: BatchQueueManager | None = None


def get_batch_queue_manager() -> BatchQueueManager:
    """Return application-wide shared singleton BatchQueueManager."""
    global _global_batch_queue_manager
    if _global_batch_queue_manager is None:
        _global_batch_queue_manager = BatchQueueManager()
    return _global_batch_queue_manager

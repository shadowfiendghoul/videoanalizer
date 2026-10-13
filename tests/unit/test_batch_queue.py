"""Unit tests for BatchQueueManager, progressive generation, and sequential render queue."""

import asyncio
import io
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import zipfile
import pytest

from videoanalizer.quiz.batch_queue import BatchQueueManager
from videoanalizer.quiz.models import (
    BatchQueueItem,
    BatchQueueItemStatus,
    BatchRenderStartRequest,
    QuizChallenge,
    QuizItem,
    DifficultyTier,
)


@pytest.fixture
def dummy_challenge():
    from videoanalizer.quiz.models import QuizTier

    tiers = []
    for tier_idx, (tier_level, color) in enumerate(
        [
            (DifficultyTier.EASY, "#22C55E"),
            (DifficultyTier.MEDIUM, "#F59E0B"),
            (DifficultyTier.HARD, "#EF4444"),
        ],
        start=1,
    ):
        questions = [
            QuizItem(
                question_number=(tier_idx - 1) * 3 + q_sub,
                question_text=f"Вопрос {(tier_idx - 1) * 3 + q_sub} о фактах",
                correct_answer="Ответ",
                fun_fact="Интересный факт",
                difficulty=tier_level,
                tier_index=tier_idx,
                theme_color=color,
                image_query="test query",
            )
            for q_sub in range(1, 4)
        ]
        tiers.append(
            QuizTier(
                tier_level=tier_level,
                tier_index=tier_idx,
                theme_color=color,
                questions=questions,
            )
        )

    return QuizChallenge(
        topic="Тестовая тема",
        language="ru",
        total_questions=9,
        tiers=tiers,
    )


@pytest.mark.asyncio
async def test_batch_init_creates_items(tmp_path, dummy_challenge):
    mgr = BatchQueueManager()
    mgr.config.output_dir = tmp_path
    mgr._history_file = tmp_path / "history.json"

    with patch.object(
        mgr.orchestrator.script_service, "generate_quiz", new_callable=AsyncMock
    ) as mock_gen:
        mock_gen.return_value = dummy_challenge

        state = await mgr.init_batch(["Тема 1", "Тема 2", "Тема 3"], language="ru")

        assert state.batch_id.startswith("bq_")
        assert len(state.items) == 3
        assert state.items[0].topic == "Тема 1"
        assert state.items[1].topic == "Тема 2"
        assert state.items[2].topic == "Тема 3"

        # Wait for background generator task to complete
        if mgr._generator_task:
            await mgr._generator_task

        assert state.items[0].status == BatchQueueItemStatus.PENDING_APPROVAL
        assert state.items[0].challenge is not None
        assert state.items[1].status == BatchQueueItemStatus.PENDING_APPROVAL


@pytest.mark.asyncio
async def test_batch_remove_and_update(tmp_path, dummy_challenge):
    mgr = BatchQueueManager()
    mgr.config.output_dir = tmp_path
    mgr._history_file = tmp_path / "history.json"

    with patch.object(
        mgr.orchestrator.script_service, "generate_quiz", new_callable=AsyncMock
    ) as mock_gen:
        mock_gen.return_value = dummy_challenge
        state = await mgr.init_batch(["Тема A", "Тема B"], language="ru")
        if mgr._generator_task:
            await mgr._generator_task

    item_to_remove = state.items[0].item_id
    assert mgr.remove_item(item_to_remove) is True
    assert len(mgr.current_state.items) == 1
    assert mgr.current_state.items[0].topic == "Тема B"
    assert mgr.current_state.items[0].index == 1


@pytest.mark.asyncio
async def test_sequential_render_with_failure_isolation(tmp_path, dummy_challenge):
    mgr = BatchQueueManager()
    mgr.config.output_dir = tmp_path
    mgr._history_file = tmp_path / "history.json"

    # Create 2 mock items
    item1 = BatchQueueItem(
        item_id="bqi_1",
        index=1,
        topic="Тема 1",
        challenge=dummy_challenge,
        status=BatchQueueItemStatus.PENDING_APPROVAL,
    )
    item2 = BatchQueueItem(
        item_id="bqi_2",
        index=2,
        topic="Тема 2",
        challenge=dummy_challenge,
        status=BatchQueueItemStatus.PENDING_APPROVAL,
    )

    fake_video = tmp_path / "fake_video.mp4"
    fake_video.write_text("dummy video content", encoding="utf-8")

    # Mock orchestrator.generate: item 1 fails, item 2 succeeds
    call_count = 0

    async def mock_generate(**kwargs):
        nonlocal call_count
        call_count += 1
        if kwargs.get("topic") == "Тема 1":
            raise RuntimeError("Remotion render error!")
        return fake_video

    with patch.object(mgr.orchestrator, "generate", side_effect=mock_generate):
        req = BatchRenderStartRequest(
            batch_id="bq_test",
            items=[item1, item2],
        )

        state = await mgr.start_render_queue(req)
        assert mgr._render_worker_task is not None
        await mgr._render_worker_task

        # Item 1 should be failed, Item 2 should be completed
        assert state.items[0].status == BatchQueueItemStatus.FAILED
        assert "Remotion render error!" in state.items[0].error_message

        assert state.items[1].status == BatchQueueItemStatus.COMPLETED
        assert state.items[1].video_path == str(fake_video)
        assert state.completed_count == 1

        # Check that history recorded the completed item
        history = mgr.get_history()
        assert len(history) == 1
        assert history[0].topic == "Тема 2"


@pytest.mark.asyncio
async def test_create_batch_zip(tmp_path, dummy_challenge):
    mgr = BatchQueueManager()
    mgr.config.output_dir = tmp_path
    mgr._history_file = tmp_path / "history.json"

    fake_video = tmp_path / "test_out.mp4"
    fake_video.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    item = BatchQueueItem(
        item_id="bqi_zip",
        index=1,
        topic="Удивительные факты",
        challenge=dummy_challenge,
        status=BatchQueueItemStatus.COMPLETED,
        video_path=str(fake_video),
    )

    from videoanalizer.quiz.models import BatchQueueState

    mgr.current_state = BatchQueueState(
        batch_id="bq_zip",
        items=[item],
        is_rendering=False,
        completed_count=1,
        total_count=1,
    )

    zip_stream = mgr.create_batch_zip()
    assert zip_stream is not None

    with zipfile.ZipFile(zip_stream, "r") as zf:
        namelist = zf.namelist()
        assert len(namelist) == 1
        assert namelist[0].endswith(".mp4")

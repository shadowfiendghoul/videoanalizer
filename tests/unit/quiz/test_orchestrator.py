"""Unit tests for QuizOrchestrator pipeline coordination and CLI command construction."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from videoanalizer.quiz.config import QuizConfig
from videoanalizer.quiz.models import (
    AudioCueSheet,
    DifficultyTier,
    QuestionAudioCue,
    QuizChallenge,
    QuizItem,
    QuizTier,
    SfxPaths,
    WordCue,
)
from videoanalizer.quiz.orchestrator import QuizOrchestrator


def make_sample_challenge() -> QuizChallenge:
    tiers = []
    configs = [
        (DifficultyTier.EASY, 1, "#22C55E", 1),
        (DifficultyTier.MEDIUM, 2, "#F59E0B", 4),
        (DifficultyTier.HARD, 3, "#EF4444", 7),
    ]
    for tier_level, tier_idx, color, start_q in configs:
        items = []
        for i in range(3):
            q_num = start_q + i
            items.append(
                QuizItem(
                    question_number=q_num,
                    difficulty=tier_level,
                    tier_index=tier_idx,
                    question_text=f"Question {q_num}?",
                    correct_answer=f"Answer {q_num}",
                    fun_fact=f"Fact {q_num}",
                    image_query=None,
                    local_image_path=None,
                )
            )
        tiers.append(
            QuizTier(
                tier_level=tier_level,
                tier_index=tier_idx,
                theme_color=color,
                questions=items,
            )
        )
    return QuizChallenge(
        topic="World Trivia",
        language="en",
        total_questions=9,
        tiers=tiers,
    )


def make_sample_cue_sheet() -> AudioCueSheet:
    cues = []
    for num in range(1, 10):
        start = (num - 1) * 360
        cues.append(
            QuestionAudioCue(
                question_number=num,
                start_frame=start,
                question_audio_file=f"audio/q{num}_question.wav",
                question_duration_ms=2000,
                question_words=[WordCue(word="Question", start_ms=0, end_ms=500)],
                think_start_frame=start + 120,
                think_duration_ms=3000,
                reveal_frame=start + 300,
                answer_audio_file=f"audio/q{num}_answer.wav",
                answer_duration_ms=1000,
                answer_words=[WordCue(word="Answer", start_ms=0, end_ms=500)],
                end_frame=start + 360,
            )
        )
    return AudioCueSheet(
        total_duration_ms=54000,
        total_duration_frames=3240,
        cues=cues,
    )


@pytest.mark.asyncio
async def test_orchestrator_build_remotion_command(tmp_path: Path) -> None:
    """Test Remotion CLI command construction with required flags."""
    config = QuizConfig(
        output_dir=tmp_path / "outputs",
        temp_dir=tmp_path / "temp",
        remotion_dir=tmp_path / "remotion",
    )
    orchestrator = QuizOrchestrator(config=config)

    props_path = tmp_path / "temp" / "props.json"
    public_dir = tmp_path / "temp" / "public"
    output_path = tmp_path / "outputs" / "final.mp4"

    cmd = orchestrator._build_remotion_command(
        props_path=props_path,
        public_dir=public_dir,
        output_path=output_path,
    )

    cmd_str = " ".join(cmd)
    assert "render" in cmd_str
    assert "src/index.ts" in cmd_str
    assert "QuizChallenge" in cmd_str
    assert f"--props={props_path.resolve()}" in cmd_str
    assert f"--public-dir={public_dir.resolve()}" in cmd_str
    assert str(output_path.resolve()) in cmd_str
    assert "--concurrency=" in cmd_str
    assert "--overwrite" in cmd_str


@pytest.mark.asyncio
async def test_orchestrator_generate_pipeline_success(tmp_path: Path) -> None:
    """Test full pipeline coordination with mocked services and subprocess."""
    config = QuizConfig(
        output_dir=tmp_path / "outputs",
        temp_dir=tmp_path / "temp",
        backgrounds_dir=tmp_path / "backgrounds",
        sfx_dir=tmp_path / "sfx",
    )
    config.backgrounds_dir.mkdir(parents=True, exist_ok=True)
    config.sfx_dir.mkdir(parents=True, exist_ok=True)
    dummy_bg = config.backgrounds_dir / "bg.mp4"
    dummy_bg.write_bytes(b"dummy bg")

    tick_file = config.sfx_dir / "timer_tick.wav"
    ding_file = config.sfx_dir / "reveal_ding.wav"
    level_file = config.sfx_dir / "level_up.wav"
    for f in (tick_file, ding_file, level_file):
        f.write_bytes(b"dummy wav")

    mock_challenge = make_sample_challenge()
    mock_cue_sheet = make_sample_cue_sheet()

    orchestrator = QuizOrchestrator(config=config)
    orchestrator.script_service = AsyncMock()
    orchestrator.script_service.generate_quiz.return_value = mock_challenge

    orchestrator.audio_service = AsyncMock()
    orchestrator.audio_service.synthesize_cue_sheet.return_value = mock_cue_sheet
    orchestrator.audio_service.ensure_default_sfx = MagicMock(
        return_value=SfxPaths(
            timer_tick=str(tick_file),
            reveal_ding=str(ding_file),
            level_up=str(level_file),
        )
    )

    async def fake_render(props_path: Path, public_dir: Path, output_path: Path) -> None:
        output_path.write_bytes(b"rendered mp4 data")

    with patch.object(orchestrator, "_render_remotion", new_callable=AsyncMock) as mock_render:
        mock_render.side_effect = fake_render

        result_path = await orchestrator.generate(
            topic="World Geography",
            language="en",
            output_filename="test_quiz.mp4",
        )

        assert result_path.name == "test_quiz.mp4"
        orchestrator.script_service.generate_quiz.assert_awaited_once()
        orchestrator.audio_service.synthesize_cue_sheet.assert_awaited_once()
        mock_render.assert_awaited_once()
        # Verify workspace directory is 100% cleaned up upon normal completion
        assert len(list(config.temp_dir.glob("quiz_*"))) == 0


@pytest.mark.asyncio
async def test_orchestrator_cleans_up_workspace_on_error(tmp_path: Path) -> None:
    """Test that temporary workspace is removed even if rendering raises an error."""
    config = QuizConfig(
        output_dir=tmp_path / "outputs",
        temp_dir=tmp_path / "temp",
        backgrounds_dir=tmp_path / "backgrounds",
        sfx_dir=tmp_path / "sfx",
    )
    config.backgrounds_dir.mkdir(parents=True, exist_ok=True)
    config.sfx_dir.mkdir(parents=True, exist_ok=True)
    (config.backgrounds_dir / "bg.mp4").write_bytes(b"bg")
    (config.sfx_dir / "timer_tick.wav").write_bytes(b"wav")
    (config.sfx_dir / "reveal_ding.wav").write_bytes(b"wav")
    (config.sfx_dir / "level_up.wav").write_bytes(b"wav")

    orchestrator = QuizOrchestrator(config=config)
    orchestrator.script_service = AsyncMock()
    orchestrator.script_service.generate_quiz.side_effect = RuntimeError("API down")

    with pytest.raises(RuntimeError, match="API down"):
        await orchestrator.generate(topic="Geography")

    # Verify temp dir is clean of job workspaces
    assert len(list(config.temp_dir.glob("quiz_*"))) == 0


def test_orchestrator_select_background(tmp_path: Path) -> None:
    """Test background selection: explicit path, filename in backgrounds dir, and random."""
    config = QuizConfig(
        output_dir=tmp_path / "outputs",
        temp_dir=tmp_path / "temp",
        backgrounds_dir=tmp_path / "backgrounds",
    )
    config.backgrounds_dir.mkdir(parents=True, exist_ok=True)
    bg1 = config.backgrounds_dir / "minecraft_parkour_1.mp4"
    bg1.write_bytes(b"bg1")
    bg2 = config.backgrounds_dir / "gta5_mega_ramp_vertical.mp4"
    bg2.write_bytes(b"bg2")

    orchestrator = QuizOrchestrator(config=config)

    # 1. By relative filename in backgrounds_dir
    selected = orchestrator.select_background("minecraft_parkour_1.mp4")
    assert selected == bg1

    # 2. By absolute Path
    selected_abs = orchestrator.select_background(bg2)
    assert selected_abs == bg2

    # 3. By "random"
    random_bg = orchestrator.select_background("random")
    assert random_bg in (bg1, bg2)

    # 4. None falls back to random from backgrounds_dir
    default_bg = orchestrator.select_background(None)
    assert default_bg in (bg1, bg2)


@pytest.mark.asyncio
async def test_orchestrator_generate_with_banner(tmp_path: Path) -> None:
    """Test banner staging and strict temporal centering calculation in Remotion props."""
    config = QuizConfig(
        output_dir=tmp_path / "outputs",
        temp_dir=tmp_path / "temp",
        backgrounds_dir=tmp_path / "backgrounds",
        banners_dir=tmp_path / "banners",
        sfx_dir=tmp_path / "sfx",
        remotion_dir=tmp_path / "remotion",
    )
    config.backgrounds_dir.mkdir(parents=True, exist_ok=True)
    config.banners_dir.mkdir(parents=True, exist_ok=True)
    config.sfx_dir.mkdir(parents=True, exist_ok=True)

    bg = config.backgrounds_dir / "default_bg.mp4"
    bg.write_bytes(b"bg")
    (config.sfx_dir / "timer_tick.wav").write_bytes(b"wav")
    (config.sfx_dir / "reveal_ding.wav").write_bytes(b"wav")
    (config.sfx_dir / "level_up.wav").write_bytes(b"wav")

    # Create dummy banner
    banner = config.banners_dir / "promo.mp4"
    banner.write_bytes(b"banner_content")

    orchestrator = QuizOrchestrator(config=config)
    sample_challenge = make_sample_challenge()
    sample_cue_sheet = make_sample_cue_sheet()  # 3240 total frames
    orchestrator.script_service = AsyncMock()
    orchestrator.script_service.generate_quiz.return_value = sample_challenge
    orchestrator.audio_service = AsyncMock()
    orchestrator.audio_service.synthesize_cue_sheet.return_value = sample_cue_sheet
    orchestrator.audio_service.ensure_default_sfx = MagicMock(
        return_value=SfxPaths(
            timer_tick=str(config.sfx_dir / "timer_tick.wav"),
            reveal_ding=str(config.sfx_dir / "reveal_ding.wav"),
            level_up=str(config.sfx_dir / "level_up.wav"),
        )
    )
    # Banner duration is 300 frames (5.0s at 60fps)
    orchestrator._probe_video_duration_frames = MagicMock(return_value=300)

    captured_props = {}

    async def mock_render(props_path: Path, public_dir: Path, output_path: Path) -> None:
        import json
        captured_props.update(json.loads(props_path.read_text(encoding="utf-8")))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"dummy_rendered_video")

    orchestrator._render_remotion = AsyncMock(side_effect=mock_render)

    res = await orchestrator.generate(
        topic="Trivia",
        background_video="default_bg.mp4",
        banner_video="promo.mp4",
    )
    assert res.exists()
    assert captured_props.get("banner_video_path") == "banner.mp4"
    # Mid-roll banner inserted between questions (after Question 4 tier transition: frame 1440)
    assert captured_props.get("banner_start_frame") == 1440


@pytest.mark.asyncio
async def test_orchestrator_generate_with_approved_challenge(tmp_path: Path) -> None:
    """Test passing pre-approved challenge bypasses script_service and uses provided questions."""
    config = QuizConfig(
        output_dir=tmp_path / "outputs",
        temp_dir=tmp_path / "temp",
        backgrounds_dir=tmp_path / "backgrounds",
        sfx_dir=tmp_path / "sfx",
        remotion_dir=tmp_path / "remotion",
    )
    config.backgrounds_dir.mkdir(parents=True, exist_ok=True)
    config.sfx_dir.mkdir(parents=True, exist_ok=True)

    bg = config.backgrounds_dir / "default_bg.mp4"
    bg.write_bytes(b"bg")
    (config.sfx_dir / "timer_tick.wav").write_bytes(b"wav")
    (config.sfx_dir / "reveal_ding.wav").write_bytes(b"wav")
    (config.sfx_dir / "level_up.wav").write_bytes(b"wav")

    orchestrator = QuizOrchestrator(config=config)
    sample_challenge = make_sample_challenge()
    sample_cue_sheet = make_sample_cue_sheet()

    orchestrator.script_service = AsyncMock()
    orchestrator.audio_service = AsyncMock()
    orchestrator.audio_service.synthesize_cue_sheet.return_value = sample_cue_sheet
    orchestrator.audio_service.ensure_default_sfx = MagicMock(
        return_value=SfxPaths(
            timer_tick=str(config.sfx_dir / "timer_tick.wav"),
            reveal_ding=str(config.sfx_dir / "reveal_ding.wav"),
            level_up=str(config.sfx_dir / "level_up.wav"),
        )
    )

    captured_props = {}

    async def mock_render(props_path: Path, public_dir: Path, output_path: Path) -> None:
        import json
        captured_props.update(json.loads(props_path.read_text(encoding="utf-8")))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"rendered_mp4")

    orchestrator._render_remotion = AsyncMock(side_effect=mock_render)

    res = await orchestrator.generate(
        topic="PreApprovedTopic",
        challenge=sample_challenge,
    )

    assert res.exists()
    # Ensure script_service was NOT called because pre-approved challenge was supplied
    orchestrator.script_service.generate_quiz.assert_not_called()
    # Ensure rendered challenge matches provided challenge
    assert captured_props["challenge"]["topic"] == "World Trivia"
    assert len(captured_props["challenge"]["tiers"]) == 3



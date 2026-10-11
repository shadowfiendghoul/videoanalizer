import React from "react";
import { AbsoluteFill, Audio, Sequence, useCurrentFrame } from "remotion";
import { AntiCheatCallout } from "./components/AntiCheatCallout";
import { BackgroundLayer } from "./components/BackgroundLayer";
import { CenterBanner } from "./components/CenterBanner";
import { CommentTrapOutro } from "./components/CommentTrapOutro";
import { DecoyFakeOut } from "./components/DecoyFakeOut";
import { KaraokeCaptions } from "./components/KaraokeCaptions";
import { LevelHeader } from "./components/LevelHeader";
import { PanicVignette } from "./components/PanicVignette";
import { QuestionLadder } from "./components/QuestionLadder";
import { RankStatusBar } from "./components/RankStatusBar";
import { StreakFire } from "./components/StreakFire";
import { StressTimer } from "./components/StressTimer";
import { DifficultyTier, RemotionRenderProps } from "./types";
import { resolveAssetUrl } from "./utils/assets";

export const QuizChallengeComp: React.FC<RemotionRenderProps> = ({
  challenge,
  cue_sheet,
  background_video_path,
  sfx_paths,
  retention,
  banner_video_path,
  banner_start_frame,
  banner_duration_frames,
}) => {
  const currentGlobalFrame = useCurrentFrame();

  return (
    <AbsoluteFill className="bg-slate-950 text-white font-sans overflow-hidden">
      {/* 1. Global Looping Background Video */}
      <BackgroundLayer videoPath={background_video_path} />

      {/* 2. Persistent Left-Side 1-9 Question & Answer Ladder */}
      <QuestionLadder
        challenge={challenge}
        cueSheet={cue_sheet}
        currentFrame={currentGlobalFrame}
      />

      {/* 3. Top Status Rank/IQ Bar (Y=150px) */}
      <RankStatusBar
        currentFrame={currentGlobalFrame}
        cueSheet={cue_sheet}
        retention={retention}
      />

      {/* 4. Top-Center Level Tier Banner (УРОВЕНЬ: ЛЕГКИЙ/СРЕДНИЙ/ТЯЖЕЛЫЙ) */}
      <LevelHeader
        cueSheet={cue_sheet}
        currentFrame={currentGlobalFrame}
        language={challenge.language}
      />

      {/* 5. Top-Right Combo Streak Flame Counter */}
      <StreakFire
        currentFrame={currentGlobalFrame}
        cueSheet={cue_sheet}
        streakConfig={retention?.streak_fire}
      />

      {/* 6. Sequence each question's audio, stress timer, and captions */}
      {cue_sheet.cues.map((cue, idx) => {
        const durationInFrames = Math.max(1, cue.end_frame - cue.start_frame);
        const thinkStartOffset = Math.max(0, cue.think_start_frame - cue.start_frame);
        const revealOffset = Math.max(0, cue.reveal_frame - cue.start_frame);
        const thinkDurationFrames = Math.max(1, revealOffset - thinkStartOffset);
        const answerDurationFrames = Math.max(1, durationInFrames - revealOffset);

        const tierLevel: DifficultyTier =
          cue.question_number <= 3
            ? "easy"
            : cue.question_number <= 6
            ? "medium"
            : "hard";

        const isHardTier = tierLevel === "hard";
        const isLevelUpQuestion =
          cue.question_number === 3 || cue.question_number === 6 || cue.question_number === 9;

        // Choose SFX for think phase: heartbeat on hard tier, else timer_tick
        const thinkSfx =
          isHardTier && sfx_paths?.heartbeat_panic
            ? sfx_paths.heartbeat_panic
            : sfx_paths?.timer_tick;

        const levelUpSfx =
          sfx_paths?.rank_levelup || sfx_paths?.level_up;

        return (
          <Sequence
            key={`question-cycle-${cue.question_number}-${idx}`}
            from={cue.start_frame}
            durationInFrames={durationInFrames}
            name={`Question ${cue.question_number}`}
          >
            {/* Level-Up SFX Stinger for tier transitions */}
            {isLevelUpQuestion && levelUpSfx && (
              <Audio src={resolveAssetUrl(levelUpSfx)} volume={0.8} />
            )}

            {/* Streak Fire Woosh on answer reveal */}
            {sfx_paths?.streak_fire && (
              <Sequence from={revealOffset} durationInFrames={30}>
                <Audio src={resolveAssetUrl(sfx_paths.streak_fire)} volume={0.65} />
              </Sequence>
            )}

            {/* Question Voiceover Audio */}
            {cue.question_audio_file && (
              <Audio src={resolveAssetUrl(cue.question_audio_file)} />
            )}

            {/* Anti-Cheat Callout on Question 9 ("👀 БЕЗ ПАУЗЫ И ГУГЛА!") */}
            <AntiCheatCallout
              currentFrame={currentGlobalFrame}
              questionNumber={cue.question_number}
              qStartFrame={cue.start_frame}
              enabled={retention?.anti_cheat_callout}
            />

            {/* Decoy Fake-Out on Q4 and Q7 (0.3s fake answer tease) */}
            <DecoyFakeOut
              currentFrame={currentGlobalFrame}
              revealFrame={cue.reveal_frame}
              questionNumber={cue.question_number}
              correctAnswer={
                challenge.tiers
                  .flatMap((t) => t.questions)
                  .find((item) => item.question_number === cue.question_number)
                  ?.correct_answer ?? ""
              }
              decoyAnswer={
                challenge.tiers
                  .flatMap((t) => t.questions)
                  .find((item) => item.question_number === cue.question_number)
                  ?.decoy_answer
              }
              enabled={retention?.enabled !== false}
            />

            {/* Question Karaoke Subtitles at bottom */}
            <Sequence from={0} durationInFrames={thinkStartOffset}>
              <KaraokeCaptions words={cue.question_words} />
            </Sequence>

            {/* Think Window: Stress Timer & Pulsing Audio */}
            <Sequence from={thinkStartOffset} durationInFrames={thinkDurationFrames}>
              {thinkSfx && (
                <Audio src={resolveAssetUrl(thinkSfx)} volume={0.75} />
              )}
            </Sequence>

            {/* Stress Timer active during think phase */}
            <CycleStressTimer
              thinkStartOffset={thinkStartOffset}
              revealOffset={revealOffset}
              tierLevel={tierLevel}
            />

            {/* Pulsing Red Panic Vignette during Hard Tier Think Phase */}
            {isHardTier && (
              <CyclePanicVignette
                thinkStartOffset={thinkStartOffset}
                revealOffset={revealOffset}
              />
            )}

            {/* Reveal Window: Reveal Ding SFX, Answer Audio, and Answer Subtitles */}
            <Sequence from={revealOffset} durationInFrames={answerDurationFrames}>
              {sfx_paths?.reveal_ding && (
                <Audio src={resolveAssetUrl(sfx_paths.reveal_ding)} volume={0.9} />
              )}
              {cue.answer_audio_file && (
                <Audio src={resolveAssetUrl(cue.answer_audio_file)} />
              )}
              <KaraokeCaptions words={cue.answer_words} />
            </Sequence>
          </Sequence>
        );
      })}

      {/* 7. Optional Center Animated Video Banner (Strictly Middle of Timeline, >=25% Screen Area) */}
      {banner_video_path &&
        typeof banner_start_frame === "number" &&
        typeof banner_duration_frames === "number" && (
          <Sequence
            from={banner_start_frame}
            durationInFrames={banner_duration_frames}
            name="CenterBanner"
          >
            <CenterBanner
              videoPath={banner_video_path}
              durationInFrames={banner_duration_frames}
            />
          </Sequence>
        )}

      {/* 8. Final 1.5s Comment Trap Outro Challenge (Controversy & Debates Hook) */}
      <CommentTrapOutro
        currentFrame={currentGlobalFrame}
        totalFrames={cue_sheet.total_duration_frames}
        config={retention?.comment_trap}
      />

      {/* Outro Buzzer SFX on Comment Trap */}
      {sfx_paths?.comment_buzzer && retention?.comment_trap?.enabled !== false && (
        <Sequence
          from={Math.max(
            0,
            cue_sheet.total_duration_frames - (retention?.comment_trap?.duration_frames ?? 90)
          )}
          durationInFrames={retention?.comment_trap?.duration_frames ?? 90}
        >
          <Audio src={resolveAssetUrl(sfx_paths.comment_buzzer)} volume={0.85} />
        </Sequence>
      )}
    </AbsoluteFill>
  );
};

// Helper component to pass relative frame to StressTimer
const CycleStressTimer: React.FC<{
  thinkStartOffset: number;
  revealOffset: number;
  tierLevel: DifficultyTier;
}> = ({ thinkStartOffset, revealOffset, tierLevel }) => {
  const currentFrameInCycle = useCurrentFrame();

  return (
    <StressTimer
      currentFrame={currentFrameInCycle}
      startFrame={thinkStartOffset}
      revealFrame={revealOffset}
      tierLevel={tierLevel}
    />
  );
};

// Helper component for Panic Vignette
const CyclePanicVignette: React.FC<{
  thinkStartOffset: number;
  revealOffset: number;
}> = ({ thinkStartOffset, revealOffset }) => {
  const currentFrameInCycle = useCurrentFrame();
  const isActive =
    currentFrameInCycle >= thinkStartOffset && currentFrameInCycle < revealOffset;

  return <PanicVignette currentFrame={currentFrameInCycle} active={isActive} />;
};


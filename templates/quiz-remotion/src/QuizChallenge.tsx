import React from "react";
import { AbsoluteFill, Audio, Sequence, useCurrentFrame } from "remotion";
import { BackgroundLayer } from "./components/BackgroundLayer";
import { CenterBanner } from "./components/CenterBanner";
import { CountdownPill } from "./components/CountdownPill";
import { KaraokeCaptions } from "./components/KaraokeCaptions";
import { LevelHeader } from "./components/LevelHeader";
import { QuestionLadder } from "./components/QuestionLadder";
import { RemotionRenderProps } from "./types";
import { resolveAssetUrl } from "./utils/assets";

export const QuizChallengeComp: React.FC<RemotionRenderProps> = ({
  challenge,
  cue_sheet,
  background_video_path,
  sfx_paths,
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

      {/* 3. Top-Center Level Tier Banner (УРОВЕНЬ: ЛЕГКИЙ/СРЕДНИЙ/ТЯЖЕЛЫЙ) */}
      <LevelHeader
        cueSheet={cue_sheet}
        currentFrame={currentGlobalFrame}
        language={challenge.language}
      />

      {/* 3. Sequence each question's audio, countdown pill, and captions */}
      {cue_sheet.cues.map((cue, idx) => {
        const durationInFrames = Math.max(1, cue.end_frame - cue.start_frame);
        const thinkStartOffset = Math.max(0, cue.think_start_frame - cue.start_frame);
        const revealOffset = Math.max(0, cue.reveal_frame - cue.start_frame);
        const thinkDurationFrames = Math.max(1, revealOffset - thinkStartOffset);
        const answerDurationFrames = Math.max(1, durationInFrames - revealOffset);

        const isLevelUpQuestion =
          cue.question_number === 5 || cue.question_number === 9;

        return (
          <Sequence
            key={`question-cycle-${cue.question_number}-${idx}`}
            from={cue.start_frame}
            durationInFrames={durationInFrames}
            name={`Question ${cue.question_number}`}
          >
            {/* Level-Up SFX Stinger for tier transitions */}
            {isLevelUpQuestion && sfx_paths?.level_up && (
              <Audio src={resolveAssetUrl(sfx_paths.level_up)} volume={0.8} />
            )}

            {/* Question Voiceover Audio */}
            {cue.question_audio_file && (
              <Audio src={resolveAssetUrl(cue.question_audio_file)} />
            )}

            {/* Question Karaoke Subtitles at bottom */}
            <Sequence from={0} durationInFrames={thinkStartOffset}>
              <KaraokeCaptions words={cue.question_words} />
            </Sequence>

            {/* 3.0s Think Window: Sleek Pill Progress Bar & Ticking SFX */}
            <Sequence from={thinkStartOffset} durationInFrames={thinkDurationFrames}>
              {sfx_paths?.timer_tick && (
                <Audio src={resolveAssetUrl(sfx_paths.timer_tick)} volume={0.7} />
              )}
            </Sequence>

            {/* Countdown Pill active during think phase */}
            <CycleCountdownPill
              thinkStartOffset={thinkStartOffset}
              revealOffset={revealOffset}
            />

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

      {/* 4. Optional Center Animated Video Banner (Strictly Middle of Timeline, >=25% Screen Area) */}
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
    </AbsoluteFill>
  );
};

// Helper component to pass relative frame to CountdownPill
const CycleCountdownPill: React.FC<{
  thinkStartOffset: number;
  revealOffset: number;
}> = ({ thinkStartOffset, revealOffset }) => {
  const currentFrameInCycle = useCurrentFrame();

  return (
    <CountdownPill
      currentFrame={currentFrameInCycle}
      startFrame={thinkStartOffset}
      revealFrame={revealOffset}
    />
  );
};

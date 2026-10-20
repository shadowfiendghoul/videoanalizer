import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  Loop,
  OffthreadVideo,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
} from "remotion";
import { WidescreenQuizRenderProps } from "./types";
import { WidescreenStatusBar } from "./components/WidescreenStatusBar";
import { WidescreenAssetContainer } from "./components/WidescreenAssetContainer";
import { WidescreenTimerBar } from "./components/WidescreenTimerBar";
import { WidescreenAnswerPanel } from "./components/WidescreenAnswerPanel";
import { WidescreenIntro } from "./components/WidescreenIntro";
import { WidescreenRoundSplash } from "./components/WidescreenRoundSplash";
import { WidescreenOutro } from "./components/WidescreenOutro";
import { WidescreenGamingPattern } from "./components/WidescreenGamingPattern";
import { WidescreenRoundTransition } from "./components/WidescreenRoundTransition";

const resolveSrc = (src?: string | null) => {
  if (!src) return undefined;
  if (src.startsWith("http://") || src.startsWith("https://") || src.startsWith("data:")) return src;
  return staticFile(src);
};

export const WidescreenGamingQuizComp: React.FC<WidescreenQuizRenderProps> = ({
  dataset,
  timing_slots,
  audio_mix_path,
  bgm_audio_path,
  sfx_ticking_path,
  sfx_chime_path,
  sfx_stinger_path,
  intro_tts_audio_path,
  outro_tts_audio_path,
  ambient_background_path,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Find active slot based on current frame
  const activeSlot = timing_slots.find(
    (s) => frame >= s.start_frame && frame < s.end_frame
  );

  // Helper map: global_question_number -> { question, round }
  const questionMap = React.useMemo(() => {
    const map = new Map<number, { question: any; round: any }>();
    if (dataset?.rounds) {
      for (const r of dataset.rounds) {
        for (const q of r.questions) {
          map.set(q.global_question_number, { question: q, round: r });
        }
      }
    }
    return map;
  }, [dataset]);

  // Helper map: round_number -> round
  const roundMap = React.useMemo(() => {
    const map = new Map<number, any>();
    if (dataset?.rounds) {
      for (const r of dataset.rounds) {
        map.set(r.round_number, r);
      }
    }
    return map;
  }, [dataset]);

  return (
    <AbsoluteFill
      style={{
        width: 1920,
        height: 1080,
        backgroundColor: "#0D1117",
        background: "radial-gradient(circle at center, #161B22 0%, #07090D 100%)",
        overflow: "hidden",
        position: "relative",
      }}
    >
      {/* 0. AMBIENT BACKGROUND VIDEO LAYER (if provided) */}
      {(ambient_background_path || dataset?.ambient_background_video) && (
        <AbsoluteFill style={{ zIndex: 0 }}>
          <Loop durationInFrames={600}>
            <OffthreadVideo
              src={resolveSrc(ambient_background_path || dataset.ambient_background_video)!}
              muted
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
              }}
            />
          </Loop>
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: "radial-gradient(circle at center, rgba(13, 17, 23, 0.65) 0%, rgba(7, 9, 13, 0.88) 100%)",
            }}
          />
        </AbsoluteFill>
      )}

      {/* Dynamic Geometric Gaming Pattern Overlay (10-15% Shimmering Gamepad Icons) */}
      <WidescreenGamingPattern />

      {/* 1. MASTER AUDIO MIX (if pre-rendered by audio_service) */}
      {audio_mix_path && <Audio src={resolveSrc(audio_mix_path)!} />}

      {/* 2. PROCEDURAL INDIVIDUAL AUDIO FALLBACKS (if master mix not supplied) */}
      {!audio_mix_path && (
        <>
          {/* Continuous BGM Track with Ducking */}
          {bgm_audio_path && (
            <Audio
              src={resolveSrc(bgm_audio_path)!}
              loop
              volume={(f) => {
                // Check if current frame falls within an audio round cue or intro/outro speech
                const slot = timing_slots.find(
                  (s) => f >= s.start_frame && f < s.end_frame
                );
                if (slot?.slot_type === "intro" || slot?.slot_type === "outro") {
                  return dataset.bgm_ducking_volume ?? 0.18;
                }
                if (
                  slot?.slot_type === "question" &&
                  slot.audio_cue_start_frame &&
                  slot.audio_cue_end_frame &&
                  f >= slot.audio_cue_start_frame &&
                  f <= slot.audio_cue_end_frame
                ) {
                  return dataset.bgm_ducking_volume ?? 0.18;
                }
                return dataset.bgm_base_volume ?? 0.30;
              }}
            />
          )}

          {/* Intro TTS */}
          {intro_tts_audio_path && timing_slots.find((s) => s.slot_type === "intro") && (
            <Sequence
              from={timing_slots.find((s) => s.slot_type === "intro")!.start_frame}
              durationInFrames={timing_slots.find((s) => s.slot_type === "intro")!.duration_frames}
            >
              <Audio src={resolveSrc(intro_tts_audio_path)!} />
            </Sequence>
          )}

          {/* Outro TTS */}
          {outro_tts_audio_path && timing_slots.find((s) => s.slot_type === "outro") && (
            <Sequence
              from={timing_slots.find((s) => s.slot_type === "outro")!.start_frame}
              durationInFrames={timing_slots.find((s) => s.slot_type === "outro")!.duration_frames}
            >
              <Audio src={resolveSrc(outro_tts_audio_path)!} />
            </Sequence>
          )}

          {/* Question SFX Sequences */}
          {timing_slots.map((slot, idx) => {
            if (slot.slot_type === "splash" && sfx_stinger_path) {
              return (
                <Sequence
                  key={`splash_sfx_${idx}`}
                  from={slot.start_frame}
                  durationInFrames={slot.duration_frames}
                >
                  <Audio src={resolveSrc(sfx_stinger_path)!} />
                </Sequence>
              );
            }

            if (slot.slot_type === "question") {
              const qData = slot.question_global_number
                ? questionMap.get(slot.question_global_number)
                : null;
              const cuePath = qData?.question?.asset_path;
              const isAudioRound = qData?.round?.asset_mode === "audio_sfx";

              return (
                <React.Fragment key={`q_sfx_${idx}`}>
                  {/* Ticking during guessing phase (frames 0 to 360) */}
                  {sfx_ticking_path && slot.timer_start_frame !== undefined && slot.timer_duration_frames && (
                    <Sequence
                      from={slot.timer_start_frame!}
                      durationInFrames={slot.timer_duration_frames!}
                    >
                      <Audio src={resolveSrc(sfx_ticking_path)!} volume={0.7} loop />
                    </Sequence>
                  )}

                  {/* Audio Round Cue Playback */}
                  {isAudioRound && cuePath && slot.audio_cue_start_frame && slot.audio_cue_end_frame && (
                    <Sequence
                      from={slot.audio_cue_start_frame}
                      durationInFrames={slot.audio_cue_end_frame - slot.audio_cue_start_frame}
                    >
                      <Audio src={resolveSrc(cuePath)!} volume={1.0} />
                    </Sequence>
                  )}

                  {/* Reveal Ding Chime at exactly 6.0s */}
                  {sfx_chime_path && slot.reveal_frame !== undefined && (
                    <Sequence
                      from={slot.reveal_frame!}
                      durationInFrames={slot.end_frame - slot.reveal_frame!}
                    >
                      <Audio src={resolveSrc(sfx_chime_path)!} volume={0.9} />
                    </Sequence>
                  )}
                </React.Fragment>
              );
            }

            return null;
          })}
        </>
      )}

      {/* 3. VISUAL STAGE SEQUENCE RENDERING */}
      {activeSlot?.slot_type === "intro" && (
        <WidescreenIntro
          challengeTitle={dataset?.intro?.challenge_title || dataset?.title || "50 GAMING QUESTIONS"}
        />
      )}

      {/* Round transitions are handled purely by the diagonal blade wipe below (no text splash screens) */}

      {activeSlot?.slot_type === "outro" && (
        <WidescreenOutro
          scoreTiers={dataset?.outro?.score_tiers || []}
          callToAction={dataset?.outro?.call_to_action || "COMMENT YOUR SCORE & SUBSCRIBE!"}
        />
      )}

      {activeSlot?.slot_type === "question" && activeSlot.question_global_number && (
        (() => {
          const qEntry = questionMap.get(activeSlot.question_global_number);
          if (!qEntry) return null;
          const { question, round } = qEntry;
          const relativeFrame = frame - activeSlot.start_frame;
          const isRevealed =
            activeSlot.reveal_frame !== undefined &&
            activeSlot.reveal_frame !== null &&
            frame >= activeSlot.reveal_frame;

          const timerDur = activeSlot.timer_duration_frames || 360;
          const panicStart = Math.max(0, timerDur - 120);
          const isPanic = relativeFrame >= panicStart && relativeFrame < timerDur;
          const panicPulse = isPanic
            ? Math.abs(Math.sin((relativeFrame - panicStart) * 0.45))
            : 0;
          const panicOpacity = isPanic
            ? interpolate(relativeFrame, [panicStart, panicStart + 40, timerDur], [0.05, 0.2 + 0.1 * panicPulse, 0.35], {
                extrapolateRight: "clamp",
              })
            : 0;

          return (
            <>
              {/* Edge Panic Vignette (Subtle edge tint in final 2.0s before answer reveal) */}
              {isPanic && (
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    pointerEvents: "none",
                    zIndex: 8,
                    opacity: panicOpacity,
                    background: "radial-gradient(ellipse at center, transparent 70%, rgba(200, 20, 50, 0.12) 88%, rgba(225, 29, 72, 0.3) 100%)",
                    boxShadow: "inset 0 0 50px rgba(225, 29, 72, 0.2)",
                  }}
                />
              )}

              {/* Top Status Bar (Round Badge + Question Tracker) */}
              <WidescreenStatusBar
                roundTitle={round.round_title}
                themeColor={round.badge_theme_color}
                currentQuestionNumber={question.global_question_number ?? question.item_index}
                totalQuestions={dataset?.total_questions_count ?? 50}
                relativeFrame={relativeFrame}
              />

              {/* Central Asset Container (1200x600 px) */}
              <WidescreenAssetContainer
                assetMode={round.asset_mode}
                assetPath={question.asset_path || (question as any).local_asset_path}
                assetUrl={question.asset_url}
                promptText={question.prompt_text}
                applyProceduralMask={question.apply_procedural_mask ?? true}
                isRevealed={isRevealed}
                themeColor={round.badge_theme_color}
                relativeFrame={relativeFrame}
              />

              {/* Countdown Timer Bar (1200x18 px) */}
              <WidescreenTimerBar
                relativeFrame={relativeFrame}
                durationFrames={timerDur}
              />

              {/* Answer Reveal Panel (1000x90 px) */}
              <WidescreenAnswerPanel
                answerText={question.answer_text}
                relativeFrame={relativeFrame}
                revealFrame={timerDur}
              />
            </>
          );
        })()
      )}

      {/* 4. HIGH-OCTANE ESPORTS ROUND TRANSITIONS (Diagonal Blade Wipe - Pure Visual, No Text) */}
      {(() => {
        // A. If in a splash slot: play the clean blade wipe for the transition
        if (activeSlot?.slot_type === "splash") {
          const relFrame = frame - activeSlot.start_frame;
          const dur = activeSlot.duration_frames;
          return <WidescreenRoundTransition relativeFrame={relFrame} durationFrames={Math.min(dur, 28)} accentColor="#FFE033" />;
        }

        // B. When starting the first question of a new round
        if (activeSlot?.slot_type === "question") {
          const relFrame = frame - activeSlot.start_frame;
          const currentIdx = timing_slots.findIndex((s) => s === activeSlot);
          const prevSlot = currentIdx > 0 ? timing_slots[currentIdx - 1] : null;
          const isNewRound = prevSlot?.round_number !== activeSlot.round_number && prevSlot?.slot_type !== "splash";
          if (isNewRound && relFrame < 28) {
            return <WidescreenRoundTransition relativeFrame={relFrame} durationFrames={28} accentColor="#FFE033" />;
          }
        }

        return null;
      })()}
    </AbsoluteFill>
  );
};

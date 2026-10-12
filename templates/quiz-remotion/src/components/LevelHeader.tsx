import React from "react";
import { spring, useVideoConfig } from "remotion";
import { AudioCueSheet } from "../types";

interface LevelHeaderProps {
  cueSheet: AudioCueSheet;
  currentFrame: number;
  language?: "ru" | "en";
}

export const LevelHeader: React.FC<LevelHeaderProps> = ({
  cueSheet,
  currentFrame,
  language = "ru",
}) => {
  const { fps } = useVideoConfig();

  // Find currently active question cue
  let activeQuestionNumber = 1;
  for (const cue of cueSheet.cues) {
    if (currentFrame >= cue.start_frame && currentFrame < cue.end_frame) {
      activeQuestionNumber = cue.question_number;
      break;
    }
    if (currentFrame < cue.start_frame) {
      activeQuestionNumber = cue.question_number;
      break;
    }
    activeQuestionNumber = cue.question_number;
  }

  // Determine tier & tier start frame for spring animation
  const isEasy = activeQuestionNumber <= 4;
  const isMedium = activeQuestionNumber >= 5 && activeQuestionNumber <= 8;
  const isHard = activeQuestionNumber >= 9;

  let tierStartFrame = 0;
  if (isMedium) {
    const cue5 = cueSheet.cues.find((c) => c.question_number === 5);
    if (cue5) tierStartFrame = cue5.start_frame;
  } else if (isHard) {
    const cue9 = cueSheet.cues.find((c) => c.question_number === 9);
    if (cue9) tierStartFrame = cue9.start_frame;
  }

  const bounce = spring({
    frame: Math.max(0, currentFrame - tierStartFrame),
    fps,
    config: {
      damping: 15,
      mass: 0.75,
      stiffness: 95,
    },
  });

  const tierColor = isEasy
    ? "#22C55E" // Vivid green
    : isMedium
    ? "#FACC15" // Bright yellow
    : "#EF4444"; // Bold red

  const prefix = language === "en" ? "LEVEL:" : "УРОВЕНЬ:";
  const tierLabel = isEasy
    ? language === "en" ? "EASY" : "ЛЕГКИЙ"
    : isMedium
    ? language === "en" ? "MEDIUM" : "СРЕДНИЙ"
    : language === "en" ? "HARD" : "ТЯЖЕЛЫЙ";

  return (
    <div className="absolute top-[330px] left-0 right-0 flex justify-center items-center z-30 pointer-events-none">
      <div
        className="inline-flex items-center gap-4 px-10 py-4 rounded-3xl backdrop-blur-md border-2 shadow-2xl"
        style={{
          backgroundColor: "rgba(10, 15, 29, 0.85)",
          borderColor: `${tierColor}66`,
          boxShadow: `0 10px 35px rgba(0, 0, 0, 0.7), 0 0 30px ${tierColor}55`,
          transform: `scale(${bounce})`,
        }}
      >
        <span className="text-white/95 font-black text-4xl md:text-5xl tracking-wider uppercase drop-shadow-[0_2px_6px_rgba(0,0,0,0.9)]">
          {prefix}
        </span>
        <span
          className="font-black text-4xl md:text-5xl tracking-wider uppercase drop-shadow-[0_2px_10px_rgba(0,0,0,0.95)]"
          style={{
            color: tierColor,
            textShadow: `0 0 24px ${tierColor}aa`,
          }}
        >
          {tierLabel}
        </span>
      </div>
    </div>
  );
};

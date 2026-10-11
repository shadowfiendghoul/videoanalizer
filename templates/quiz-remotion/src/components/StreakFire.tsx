import React from "react";
import { spring, useVideoConfig } from "remotion";
import { AudioCueSheet, ComboStreakConfig } from "../types";

interface StreakFireProps {
  currentFrame: number;
  cueSheet: AudioCueSheet;
  streakConfig?: ComboStreakConfig;
}

export const StreakFire: React.FC<StreakFireProps> = ({
  currentFrame,
  cueSheet,
  streakConfig,
}) => {
  const { fps } = useVideoConfig();

  if (streakConfig && streakConfig.enabled === false) {
    return null;
  }

  // Calculate streak based on how many answers have been revealed
  let currentStreak = 0;
  let lastRevealFrame = 0;

  for (const cue of cueSheet.cues) {
    if (currentFrame >= cue.reveal_frame) {
      currentStreak = cue.question_number;
      lastRevealFrame = cue.reveal_frame;
    }
  }

  if (currentStreak < 1) {
    return null;
  }

  const ultraThreshold = streakConfig?.ultra_threshold ?? 7;
  const isUltra = currentStreak >= ultraThreshold;
  const normalColor = streakConfig?.fire_color_normal ?? "#FF4500";
  const ultraColor = streakConfig?.fire_color_ultra ?? "#38BDF8";
  const activeColor = isUltra ? ultraColor : normalColor;

  const bounce = spring({
    frame: Math.max(0, currentFrame - lastRevealFrame),
    fps,
    config: {
      damping: 12,
      mass: 0.5,
      stiffness: 160,
    },
  });

  return (
    <div
      style={{
        transform: `scale(${bounce})`,
        borderColor: activeColor,
        boxShadow: `0 0 20px ${activeColor}`,
      }}
      className="absolute top-[280px] right-[40px] z-30 flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-black/70 border-2 backdrop-blur-md pointer-events-none transition-all duration-100"
    >
      <span className="text-2xl drop-shadow-md">
        {isUltra ? "⚡🔥" : "🔥"}
      </span>
      <span
        style={{ color: activeColor }}
        className="font-black text-xl tracking-wider font-mono drop-shadow-sm"
      >
        x{currentStreak}
      </span>
      {isUltra && (
        <span className="text-[10px] font-black uppercase tracking-widest text-[#38BDF8] ml-1 px-1.5 py-0.5 rounded bg-[#38BDF8]/20 border border-[#38BDF8]/40 animate-pulse">
          ULTRA
        </span>
      )}
    </div>
  );
};

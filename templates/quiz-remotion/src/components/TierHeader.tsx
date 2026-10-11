import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { DifficultyTier } from "../types";

interface TierHeaderProps {
  topic: string;
  difficulty: DifficultyTier;
  questionNumber: number;
  totalQuestions: number;
  themeColor: string;
}

const TIER_LABELS: Record<DifficultyTier, { level: string; label: string }> = {
  easy: { level: "LEVEL 1", label: "EASY" },
  medium: { level: "LEVEL 2", label: "MEDIUM" },
  hard: { level: "LEVEL 3", label: "HARD" },
};

export const TierHeader: React.FC<TierHeaderProps> = ({
  topic,
  difficulty,
  questionNumber,
  totalQuestions,
  themeColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({
    frame,
    fps,
    config: {
      damping: 14,
      mass: 0.6,
      stiffness: 120,
    },
  });

  const tierInfo = TIER_LABELS[difficulty] || { level: "LEVEL", label: difficulty.toUpperCase() };

  return (
    <div
      className="absolute top-16 left-0 right-0 flex flex-col items-center justify-center px-8 z-20 pointer-events-none"
      style={{
        transform: `scale(${scale})`,
        transformOrigin: "top center",
      }}
    >
      {/* Topic Title */}
      <div className="text-white/80 text-xl font-bold uppercase tracking-widest drop-shadow mb-3 text-center">
        {topic}
      </div>

      {/* Glassmorphic Capsule Header */}
      <div
        className="flex items-center justify-between w-full max-w-[920px] px-6 py-4 rounded-3xl backdrop-blur-xl border border-white/20 shadow-2xl"
        style={{
          background: "rgba(15, 23, 42, 0.75)",
          boxShadow: `0 8px 32px 0 rgba(0, 0, 0, 0.37), 0 0 20px ${themeColor}33`,
          borderColor: `${themeColor}66`,
        }}
      >
        {/* Difficulty Badge */}
        <div
          className="flex items-center gap-2 px-4 py-1.5 rounded-full font-black text-sm uppercase tracking-wider text-slate-950"
          style={{
            backgroundColor: themeColor,
            boxShadow: `0 0 15px ${themeColor}99`,
          }}
        >
          <span>{tierInfo.level}:</span>
          <span>{tierInfo.label}</span>
        </div>

        {/* Counter Badge */}
        <div className="flex items-center gap-1 font-mono font-black text-2xl text-white">
          <span style={{ color: themeColor }}>{questionNumber}</span>
          <span className="text-white/40 font-light">/</span>
          <span className="text-white/80">{totalQuestions}</span>
        </div>
      </div>
    </div>
  );
};

import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import { AudioCueSheet, QuizRetentionConfig, RankTierConfig } from "../types";

interface RankStatusBarProps {
  currentFrame: number;
  cueSheet: AudioCueSheet;
  retention?: QuizRetentionConfig;
}

const DEFAULT_TIERS: RankTierConfig[] = [
  {
    min_question: 1,
    max_question: 2,
    rank_title: "NPC",
    rank_color: "#64748B",
    rank_icon: "🤡",
    iq_label: "IQ: 85",
  },
  {
    min_question: 3,
    max_question: 5,
    rank_title: "Нормис",
    rank_color: "#22C55E",
    rank_icon: "🤓",
    iq_label: "IQ: 110",
  },
  {
    min_question: 6,
    max_question: 8,
    rank_title: "Эрудит",
    rank_color: "#A855F7",
    rank_icon: "🧠",
    iq_label: "IQ: 135",
  },
  {
    min_question: 9,
    max_question: 9,
    rank_title: "1% ГЕНИЕВ",
    rank_color: "#F59E0B",
    rank_icon: "👑",
    iq_label: "IQ: 160+",
  },
];

export const RankStatusBar: React.FC<RankStatusBarProps> = ({
  currentFrame,
  cueSheet,
  retention,
}) => {
  const { fps } = useVideoConfig();

  if (retention && retention.enabled === false) {
    return null;
  }
  if (retention && retention.rank_bar_enabled === false) {
    return null;
  }

  const tiers = retention?.rank_tiers?.length ? retention.rank_tiers : DEFAULT_TIERS;

  // Determine active question
  let activeQ = 1;
  let qStartFrame = 0;
  for (const cue of cueSheet.cues) {
    if (currentFrame >= cue.start_frame && currentFrame < cue.end_frame) {
      activeQ = cue.question_number;
      qStartFrame = cue.start_frame;
      break;
    }
    if (currentFrame < cue.start_frame) {
      activeQ = cue.question_number;
      qStartFrame = cue.start_frame;
      break;
    }
    activeQ = cue.question_number;
    qStartFrame = cue.start_frame;
  }

  // Find active tier
  const activeTier =
    tiers.find((t) => activeQ >= t.min_question && activeQ <= t.max_question) ||
    tiers[0];

  // Calculate percentage of bar (1..9 -> 11%..100%)
  const targetPercent = Math.min(100, Math.round((activeQ / 9) * 100));

  const fillSpring = spring({
    frame: Math.max(0, currentFrame - qStartFrame),
    fps,
    config: {
      damping: 16,
      mass: 0.6,
      stiffness: 120,
    },
  });

  const animatedPercent = interpolate(fillSpring, [0, 1], [Math.max(10, targetPercent - 11), targetPercent], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const isMaxRank = activeQ === 9;

  return (
    <div className="absolute top-[150px] left-1/2 -translate-x-1/2 z-40 w-[680px] flex flex-col items-center pointer-events-none">
      {/* Top Header Badge */}
      <div className="flex items-center justify-between w-full px-3 mb-1.5 text-xs font-black tracking-wider uppercase">
        <div className="flex items-center gap-1.5 bg-black/60 backdrop-blur-md px-3 py-1 rounded-full border border-white/15">
          <span className="text-base">{activeTier.rank_icon}</span>
          <span style={{ color: activeTier.rank_color }} className="font-extrabold text-sm drop-shadow-sm">
            {activeTier.rank_title}
          </span>
        </div>
        <div className="bg-black/60 backdrop-blur-md px-3 py-1 rounded-full border border-white/15 text-white/90 font-mono text-xs">
          {activeTier.iq_label}
        </div>
      </div>

      {/* Progress Track */}
      <div className="w-full h-3 rounded-full bg-slate-900/80 p-[2px] border border-white/20 backdrop-blur-md overflow-hidden relative shadow-[0_4px_16px_rgba(0,0,0,0.6)]">
        <div
          style={{
            width: `${animatedPercent}%`,
            backgroundColor: activeTier.rank_color,
            boxShadow: `0 0 14px ${activeTier.rank_color}`,
          }}
          className={`h-full rounded-full transition-all duration-75 relative ${
            isMaxRank ? "animate-pulse" : ""
          }`}
        >
          {/* Shimmer light streak */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent animate-shimmer" />
        </div>
      </div>
    </div>
  );
};

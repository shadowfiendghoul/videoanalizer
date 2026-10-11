import React from "react";
import { spring, useVideoConfig } from "remotion";

interface AntiCheatCalloutProps {
  currentFrame: number;
  questionNumber: number;
  qStartFrame: number;
  enabled?: boolean;
}

export const AntiCheatCallout: React.FC<AntiCheatCalloutProps> = ({
  currentFrame,
  questionNumber,
  qStartFrame,
  enabled = true,
}) => {
  const { fps } = useVideoConfig();

  // Show only on Question 9
  if (!enabled || questionNumber !== 9) {
    return null;
  }

  const entrance = spring({
    frame: Math.max(0, currentFrame - qStartFrame),
    fps,
    config: {
      damping: 10,
      mass: 0.5,
      stiffness: 180,
    },
  });

  return (
    <div
      style={{
        transform: `scale(${entrance}) rotate(-3deg)`,
      }}
      className="absolute top-[280px] left-[50px] z-30 flex items-center gap-2 px-4 py-1.5 rounded-xl bg-red-600/90 text-white font-black text-sm uppercase tracking-widest border-2 border-white/80 shadow-[0_0_20px_rgba(239,68,68,0.8)] pointer-events-none animate-pulse"
    >
      <span>👀</span>
      <span>БЕЗ ПАУЗЫ И ГУГЛА!</span>
    </div>
  );
};

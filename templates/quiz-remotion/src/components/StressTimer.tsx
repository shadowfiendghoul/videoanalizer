import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import { DifficultyTier } from "../types";

interface StressTimerProps {
  currentFrame: number;
  startFrame: number;
  revealFrame: number;
  tierLevel?: DifficultyTier;
  overrideColor?: string;
}

export const StressTimer: React.FC<StressTimerProps> = ({
  currentFrame,
  startFrame,
  revealFrame,
  tierLevel = "easy",
  overrideColor,
}) => {
  const { fps } = useVideoConfig();

  if (currentFrame < startFrame || currentFrame >= revealFrame) {
    return null;
  }

  const durationFrames = Math.max(1, revealFrame - startFrame);
  const remainingFrames = Math.max(0, revealFrame - currentFrame);
  const progressPercent = interpolate(
    currentFrame,
    [startFrame, revealFrame],
    [100, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  const entrance = spring({
    frame: currentFrame - startFrame,
    fps,
    config: {
      damping: 15,
      mass: 0.6,
      stiffness: 160,
    },
  });

  // Color logic
  let barColor = overrideColor || "#00A3FF";
  let glowColor = "rgba(0,163,255,0.8)";
  let isShaking = false;

  if (!overrideColor) {
    if (tierLevel === "easy") {
      barColor = "#00A3FF"; // Calm blue
      glowColor = "rgba(0,163,255,0.8)";
    } else if (tierLevel === "medium") {
      barColor = "#F59E0B"; // Amber
      glowColor = "rgba(245,158,11,0.85)";
      if (remainingFrames <= fps) {
        isShaking = true;
      }
    } else {
      barColor = "#EF4444"; // Panic Crimson
      glowColor = "rgba(239,68,68,0.95)";
      isShaking = true;
    }
  }

  // Jitter shake calculation during panic phase
  let shakeOffset = 0;
  if (isShaking) {
    const frequency = tierLevel === "hard" ? 0.8 : 0.4;
    shakeOffset = Math.sin(currentFrame * frequency) * (tierLevel === "hard" ? 4 : 2);
  }

  return (
    <div
      style={{
        transform: `translateX(calc(-50% + ${shakeOffset}px)) scale(${entrance})`,
        filter: "drop-shadow(0px 6px 14px rgba(0, 0, 0, 0.7))",
      }}
      className="absolute bottom-72 left-1/2 z-30 flex items-center justify-center pointer-events-none"
    >
      <div className="w-[440px] h-[38px] rounded-full border-2 border-white/90 bg-black/60 p-[3px] backdrop-blur-md overflow-hidden flex items-center shadow-2xl">
        <div
          style={{
            width: `${progressPercent}%`,
            backgroundColor: barColor,
            boxShadow: `0 0 16px ${glowColor}`,
          }}
          className="h-full rounded-full transition-all duration-75 relative"
        >
          {/* Internal gradient shine */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/20 via-transparent to-white/30" />
        </div>
      </div>
    </div>
  );
};

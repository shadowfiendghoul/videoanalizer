import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";

interface CountdownPillProps {
  currentFrame: number;
  startFrame: number;
  revealFrame: number;
}

export const CountdownPill: React.FC<CountdownPillProps> = ({
  currentFrame,
  startFrame,
  revealFrame,
}) => {
  const { fps } = useVideoConfig();

  if (currentFrame < startFrame || currentFrame >= revealFrame) {
    return null;
  }

  const durationFrames = Math.max(1, revealFrame - startFrame);
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

  return (
    <div
      style={{
        transform: `translateX(-50%) scale(${entrance})`,
        filter: "drop-shadow(0px 4px 10px rgba(0, 0, 0, 0.6))",
      }}
      className="absolute bottom-72 left-1/2 z-30 flex items-center justify-center pointer-events-none"
    >
      <div className="w-[420px] h-[36px] rounded-full border-2 border-white bg-black/50 p-[3px] backdrop-blur-sm overflow-hidden flex items-center">
        <div
          style={{
            width: `${progressPercent}%`,
          }}
          className="h-full rounded-full bg-gradient-to-r from-[#00A3FF] to-[#38BDF8] shadow-[0_0_12px_rgba(0,163,255,0.8)] transition-all duration-75"
        />
      </div>
    </div>
  );
};

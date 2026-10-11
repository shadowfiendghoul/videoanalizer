import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

interface CountdownBarProps {
  durationFrames: number;
  themeColor: string;
}

export const CountdownBar: React.FC<CountdownBarProps> = ({
  durationFrames,
  themeColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Progress percentage depletes from 100% down to 0%
  const progress = interpolate(frame, [0, durationFrames], [100, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Seconds remaining (3.0s down to 0.0s)
  const remainingSec = Math.max(0, (durationFrames - frame) / fps).toFixed(1);

  return (
    <div className="absolute top-[820px] left-0 right-0 flex flex-col items-center justify-center px-8 z-20 pointer-events-none">
      <div className="w-full max-w-[960px] flex flex-col items-center gap-3">
        {/* Timer Label and Numerical Seconds */}
        <div className="flex items-center justify-between w-full px-2">
          <div className="flex items-center gap-2">
            <span className="text-xl">⏱️</span>
            <span className="font-bold text-white/70 uppercase tracking-widest text-sm">
              Time Remaining
            </span>
          </div>
          <div
            className="font-mono font-black text-2xl tracking-wider px-3 py-1 rounded-xl bg-black/50 border border-white/10"
            style={{ color: themeColor, textShadow: `0 0 10px ${themeColor}88` }}
          >
            {remainingSec}s
          </div>
        </div>

        {/* Progress Bar Track */}
        <div className="w-full h-6 bg-slate-900/80 rounded-full p-1 border border-white/20 shadow-inner overflow-hidden relative">
          {/* Animated Fill Bar */}
          <div
            className="h-full rounded-full transition-all duration-75 relative"
            style={{
              width: `${progress}%`,
              backgroundColor: themeColor,
              boxShadow: `0 0 20px ${themeColor}, 0 0 40px ${themeColor}66`,
            }}
          >
            {/* Shimmer / Glow Head */}
            <div className="absolute right-0 top-0 bottom-0 w-3 bg-white/80 rounded-full shadow-lg" />
          </div>
        </div>
      </div>
    </div>
  );
};

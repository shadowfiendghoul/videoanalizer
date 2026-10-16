import React from "react";
import { useCurrentFrame, interpolate, interpolateColors } from "remotion";
import { VisualQuizTimingSlot } from "../types";

interface SyncHorizontalTimerProps {
  timingSlots: VisualQuizTimingSlot[];
  hookEndFrame: number;
}

export const SyncHorizontalTimer: React.FC<SyncHorizontalTimerProps> = ({
  timingSlots,
  hookEndFrame,
}) => {
  const frame = useCurrentFrame();

  if (frame < hookEndFrame) {
    return null;
  }

  // Find active slot where timer is running
  const activeSlot = timingSlots.find(
    (s) =>
      frame >= s.timer_start_frame &&
      frame <= s.timer_start_frame + s.timer_duration_frames
  );

  if (!activeSlot) {
    return null;
  }

  const elapsed = frame - activeSlot.timer_start_frame;
  const progress = interpolate(
    elapsed,
    [0, activeSlot.timer_duration_frames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const barColor = interpolateColors(
    progress,
    [0, 0.35, 1],
    ["#EF4444", "#FACC15", "#00E676"]
  );

  return (
    <div
      style={{
        position: "absolute",
        left: 125,
        top: 1350,
        width: 815,
        height: 20,
      }}
      className="rounded-full bg-black/60 border-2 border-white/20 p-0.5 flex items-center shadow-lg z-20 pointer-events-none select-none"
    >
      <div
        className="h-full rounded-full transition-all"
        style={{
          width: `${progress * 100}%`,
          backgroundColor: barColor,
          boxShadow: `0 0 16px ${barColor}`,
        }}
      />
    </div>
  );
};

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

  // Dynamic vibrant neon colors: Cyan/Emerald -> Gold/Orange -> Crimson/Hot-Pink
  const primaryColor = interpolateColors(
    progress,
    [0, 0.25, 0.6, 1],
    ["#FF2A6D", "#FF9F1C", "#10B981", "#00F0FF"]
  );
  const secondaryColor = interpolateColors(
    progress,
    [0, 0.25, 0.6, 1],
    ["#800020", "#C84B00", "#047857", "#0284C7"]
  );

  // Panic pulse effect when time is running out (<25%)
  const panicOpacity = progress < 0.25 ? 0.78 + 0.22 * Math.sin(frame * 0.9) : 1;

  return (
    <div
      style={{
        position: "absolute",
        left: 110,
        top: 1290,
        width: 860,
        height: 28,
        borderRadius: 9999,
        background:
          "linear-gradient(180deg, rgba(8, 12, 24, 0.92) 0%, rgba(15, 23, 42, 0.85) 100%)",
        backdropFilter: "blur(16px)",
        border: "2px solid rgba(255, 255, 255, 0.28)",
        boxShadow:
          "0 12px 36px rgba(0, 0, 0, 0.8), inset 0 2px 6px rgba(0, 0, 0, 0.6), 0 0 20px rgba(0, 0, 0, 0.4)",
        padding: 3,
        overflow: "visible",
      }}
      className="z-20 pointer-events-none select-none flex items-center"
    >
      {/* Background track subtle segment ticks */}
      <div
        style={{
          position: "absolute",
          left: "25%",
          top: 4,
          bottom: 4,
          width: 2,
          backgroundColor: "rgba(255, 255, 255, 0.12)",
          borderRadius: 1,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: 4,
          bottom: 4,
          width: 2,
          backgroundColor: "rgba(255, 255, 255, 0.12)",
          borderRadius: 1,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: "75%",
          top: 4,
          bottom: 4,
          width: 2,
          backgroundColor: "rgba(255, 255, 255, 0.12)",
          borderRadius: 1,
        }}
      />

      {/* Shrinking progress fill bar with specular glass sheen & glow */}
      <div
        style={{
          width: `${progress * 100}%`,
          height: "100%",
          borderRadius: 9999,
          background: `linear-gradient(90deg, ${secondaryColor} 0%, ${primaryColor} 100%)`,
          boxShadow: `0 0 18px ${primaryColor}cc, 0 0 32px ${primaryColor}66`,
          position: "relative",
          opacity: panicOpacity,
          transition: "width 0.05s linear",
        }}
      >
        {/* Specular gloss top highlight */}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: 0,
            height: "50%",
            borderRadius: "9999px 9999px 0 0",
            background:
              "linear-gradient(180deg, rgba(255, 255, 255, 0.45) 0%, rgba(255, 255, 255, 0.05) 100%)",
          }}
        />

        {/* Leading edge energy spark */}
        {progress > 0.015 && (
          <div
            style={{
              position: "absolute",
              right: -3,
              top: "50%",
              transform: "translate(0, -50%)",
              width: 14,
              height: 14,
              borderRadius: "50%",
              backgroundColor: "#FFFFFF",
              boxShadow: `0 0 8px 2px #FFFFFF, 0 0 16px 4px ${primaryColor}`,
            }}
          />
        )}
      </div>
    </div>
  );
};


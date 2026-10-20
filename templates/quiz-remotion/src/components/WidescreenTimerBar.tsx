import React from "react";
import { interpolate } from "remotion";

interface WidescreenTimerBarProps {
  relativeFrame: number;
  durationFrames?: number; // default 360 frames (6.0s at 60fps)
}

export const WidescreenTimerBar: React.FC<WidescreenTimerBarProps> = ({
  relativeFrame,
  durationFrames = 360,
}) => {
  // Linearly shrink width from 1200px to 0px over durationFrames
  const width = interpolate(relativeFrame, [0, durationFrames], [1200, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Panic mode: last 2.0 seconds (120 frames at 60fps)
  const panicStartFrame = Math.max(0, durationFrames - 120);
  const isPanic = relativeFrame >= panicStartFrame && relativeFrame < durationFrames;

  // Rapid heartbeat pulse in panic phase (~2.2 pulses per second)
  const panicPulse = isPanic
    ? Math.abs(Math.sin((relativeFrame - panicStartFrame) * 0.45))
    : 0;

  // Dynamic colors and shadows (toned-down red panic)
  const barBackground = isPanic
    ? `linear-gradient(90deg, #E11D48 0%, #F43F5E 100%)`
    : `linear-gradient(90deg, #00B4D8 0%, #00F0FF 100%)`;

  const barShadow = isPanic
    ? `0 0 ${8 + panicPulse * 6}px #F43F5E, 0 0 ${18 + panicPulse * 8}px rgba(244, 63, 94, 0.4)`
    : `0 0 16px #00F0FF, 0 0 35px rgba(0, 240, 255, 0.55)`;

  return (
    <div
      style={{
        position: "absolute",
        left: 360,
        top: 795,
        width: 1200,
        height: 18,
        borderRadius: 10,
        backgroundColor: "#0B0E14",
        border: isPanic
          ? `1px solid rgba(244, 63, 94, ${0.25 + panicPulse * 0.25})`
          : "1px solid rgba(0, 240, 255, 0.2)",
        boxShadow: "inset 0 2px 6px rgba(0, 0, 0, 0.8), 0 6px 20px rgba(0, 0, 0, 0.6)",
        overflow: "hidden",
        zIndex: 10,
        transition: "border-color 0.15s ease",
      }}
    >
      <div
        style={{
          width,
          height: "100%",
          borderRadius: 8,
          background: barBackground,
          boxShadow: barShadow,
          transition: "box-shadow 0.08s ease",
        }}
      />
    </div>
  );
};

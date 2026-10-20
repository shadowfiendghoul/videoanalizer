import React from "react";
import { interpolate, interpolateColors } from "remotion";

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

  // Calculate percentage of depletion (0.0 to 1.0)
  const progress = Math.min(1.0, Math.max(0.0, relativeFrame / durationFrames));

  // Color transitions from Amber (#F59E0B) to Red (#EF4444) in the final 1.5s (progress 0.75 to 1.0)
  const barColor = interpolateColors(
    progress,
    [0, 0.75, 1.0],
    ["#F59E0B", "#F59E0B", "#EF4444"]
  );

  return (
    <div
      style={{
        position: "absolute",
        left: 360,
        top: 800,
        width: 1200,
        height: 16,
        borderRadius: 8,
        backgroundColor: "#21262D",
        boxShadow: "inset 0 2px 4px rgba(0, 0, 0, 0.5)",
        overflow: "hidden",
        zIndex: 10,
      }}
    >
      <div
        style={{
          width,
          height: "100%",
          borderRadius: 8,
          backgroundColor: barColor,
          boxShadow: `0 0 12px ${barColor}`,
          transition: "background-color 0.1s linear",
        }}
      />
    </div>
  );
};

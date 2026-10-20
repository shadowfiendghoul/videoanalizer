import React from "react";
import { interpolate } from "remotion";

interface WidescreenTimerBarProps {
  relativeFrame: number;
  durationFrames?: number; // default 360 frames (6.0s at 60fps)
  containerLeft?: number;
  containerTop?: number;
  containerWidth?: number;
  containerHeight?: number;
}

export const WidescreenTimerBar: React.FC<WidescreenTimerBarProps> = ({
  relativeFrame,
  durationFrames = 360,
  containerLeft = 230,
  containerTop = 926,
  containerWidth = 1460,
  containerHeight = 22,
}) => {
  // Linearly shrink width from containerWidth to 0px over durationFrames
  const width = interpolate(relativeFrame, [0, durationFrames], [containerWidth, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Panic mode: last 2.0 seconds (120 frames at 60fps)
  const panicStartFrame = Math.max(0, durationFrames - 120);
  const isPanic = relativeFrame >= panicStartFrame && relativeFrame < durationFrames;

  // Subtle heartbeat pulse in panic phase
  const panicPulse = isPanic
    ? Math.abs(Math.sin((relativeFrame - panicStartFrame) * 0.45))
    : 0;

  // Solid hot pink matching TOTAL pill, softly pulsing in panic
  const barColor = isPanic
    ? (panicPulse > 0.6 ? "#F43F5E" : "#E6007A")
    : "#E6007A";

  const barShadow = isPanic
    ? `0 0 ${8 + panicPulse * 6}px rgba(244, 63, 94, 0.5)`
    : "none";

  return (
    <div
      style={{
        position: "absolute",
        left: containerLeft,
        top: containerTop,
        width: containerWidth,
        height: containerHeight,
        borderRadius: 6,
        backgroundColor: "#FFFFFF",
        boxShadow: "0 6px 18px rgba(0, 0, 0, 0.5)",
        overflow: "hidden",
        zIndex: 10,
      }}
    >
      <div
        style={{
          width,
          height: "100%",
          borderRadius: 6,
          backgroundColor: barColor,
          boxShadow: barShadow,
          transition: "background-color 0.1s ease",
        }}
      />
    </div>
  );
};

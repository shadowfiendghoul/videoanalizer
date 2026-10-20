import React from "react";
import { interpolate } from "remotion";

interface WidescreenRoundTransitionProps {
  relativeFrame: number; // 0 to durationFrames
  durationFrames?: number; // default 24 frames (~0.4s at 60fps)
  accentColor?: string;
}

export const WidescreenRoundTransition: React.FC<WidescreenRoundTransitionProps> = ({
  relativeFrame,
  durationFrames = 24,
  accentColor = "#FFDE00",
}) => {
  if (relativeFrame < 0 || relativeFrame >= durationFrames) {
    return null;
  }

  // Blade 1: Golden-Yellow Gaming Stripe
  const blade1X = interpolate(relativeFrame, [0, durationFrames * 0.75], [-2400, 2400], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Blade 2: Magenta-Pink Gaming Stripe
  const blade2X = interpolate(relativeFrame, [2, durationFrames * 0.85], [-2400, 2400], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Blade 3: Main Dark Cyber Curtain with Accent Edge
  const blade3X = interpolate(relativeFrame, [4, durationFrames], [-2400, 2400], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Central impact flash (frames 9-15)
  const flashOpacity = interpolate(
    relativeFrame,
    [durationFrames * 0.35, durationFrames * 0.48, durationFrames * 0.65],
    [0, 0.75, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        zIndex: 50,
        overflow: "hidden",
      }}
    >
      {/* Blade 1: Yellow Neon Runner */}
      <div
        style={{
          position: "absolute",
          top: -200,
          left: 0,
          width: 800,
          height: 1480,
          background: "linear-gradient(90deg, transparent, #FFE033 40%, #F59E0B 100%)",
          transform: `translateX(${blade1X}px) skewX(-24deg)`,
          boxShadow: "0 0 50px rgba(245, 158, 11, 0.8)",
          opacity: 0.9,
        }}
      />

      {/* Blade 2: Magenta-Pink Runner */}
      <div
        style={{
          position: "absolute",
          top: -200,
          left: 0,
          width: 850,
          height: 1480,
          background: "linear-gradient(90deg, transparent, #F43F5E 30%, #D946EF 100%)",
          transform: `translateX(${blade2X}px) skewX(-24deg)`,
          boxShadow: "0 0 60px rgba(244, 63, 94, 0.85)",
          opacity: 0.92,
        }}
      />

      {/* Blade 3: Obsidian Cyber Slicer with Cyan Border */}
      <div
        style={{
          position: "absolute",
          top: -200,
          left: 0,
          width: 1400,
          height: 1480,
          background: "linear-gradient(90deg, rgba(8, 11, 17, 0.95), #0B0E14 70%, #161B26 100%)",
          borderRight: "6px solid #00F0FF",
          borderLeft: `6px solid ${accentColor}`,
          transform: `translateX(${blade3X}px) skewX(-24deg)`,
          boxShadow: "0 0 80px rgba(0, 0, 0, 0.9), 0 0 40px rgba(0, 240, 255, 0.6)",
        }}
      />

      {/* Flash impact */}
      {flashOpacity > 0.02 && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundColor: "#FFFFFF",
            opacity: flashOpacity,
            mixBlendMode: "screen",
          }}
        />
      )}
    </div>
  );
};

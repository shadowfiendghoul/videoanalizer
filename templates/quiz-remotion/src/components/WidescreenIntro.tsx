import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

interface WidescreenIntroProps {
  challengeTitle: string;
}

export const WidescreenIntro: React.FC<WidescreenIntroProps> = ({
  challengeTitle,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Zoom and opacity animations
  const scale = interpolate(frame, [0, fps * 8], [0.92, 1.08], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const opacity = interpolate(
    frame,
    [0, 15, fps * 8 - 15, fps * 8],
    [0, 1, 1, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        top: 0,
        width: 1920,
        height: 1080,
        backgroundColor: "#07090D",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        opacity,
        zIndex: 20,
      }}
    >
      <div
        style={{
          transform: `scale(${scale})`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          textAlign: "center",
          padding: 40,
        }}
      >
        <div
          style={{
            width: 90,
            height: 90,
            borderRadius: 24,
            backgroundColor: "#161B22",
            border: "2px solid #00E5FF",
            boxShadow: "0 0 30px rgba(0, 229, 255, 0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 24,
          }}
        >
          <span style={{ fontSize: 44 }}>🎮</span>
        </div>

        <div
          style={{
            fontFamily: "system-ui, -apple-system, sans-serif",
            fontSize: 60,
            fontWeight: 900,
            color: "#FFFFFF",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            maxWidth: 1400,
            marginBottom: 20,
            textShadow: "0 4px 24px rgba(0, 0, 0, 0.8)",
          }}
        >
          {challengeTitle}
        </div>

        <div
          style={{
            fontFamily: "system-ui, sans-serif",
            fontSize: 26,
            fontWeight: 700,
            letterSpacing: "0.15em",
            color: "#00E5FF",
            textTransform: "uppercase",
          }}
        >
          5 UNIQUE ROUNDS &nbsp;●&nbsp; CAN YOU ACHIEVE GOD TIER?
        </div>
      </div>
    </div>
  );
};

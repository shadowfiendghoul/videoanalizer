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
        background: "radial-gradient(circle at center, #16202E 0%, #06080B 100%)",
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
            width: 96,
            height: 96,
            borderRadius: 24,
            background: "linear-gradient(135deg, #00F0FF 0%, #3B82F6 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 28,
            boxShadow: "0 0 40px rgba(0, 240, 255, 0.6), inset 0 2px 2px rgba(255, 255, 255, 0.5)",
          }}
        >
          <span style={{ fontSize: 46 }}>🏆</span>
        </div>

        <div
          style={{
            fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
            fontSize: 20,
            fontWeight: 900,
            letterSpacing: "0.25em",
            color: "#00F0FF",
            textTransform: "uppercase",
            marginBottom: 16,
            textShadow: "0 0 16px rgba(0, 240, 255, 0.8)",
          }}
        >
          THE ULTIMATE GAMING TRIVIA
        </div>

        <div
          style={{
            fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
            fontSize: 64,
            fontWeight: 900,
            letterSpacing: "0.04em",
            color: "#FFFFFF",
            textTransform: "uppercase",
            maxWidth: 1400,
            lineHeight: 1.15,
            textShadow: "0 0 40px rgba(0, 240, 255, 0.4), 0 6px 24px rgba(0, 0, 0, 0.95)",
            WebkitTextStroke: "1px rgba(0, 0, 0, 0.7)",
          }}
        >
          {challengeTitle}
        </div>
      </div>
    </div>
  );
};

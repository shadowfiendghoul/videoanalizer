import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

interface WidescreenRoundSplashProps {
  roundNumber: number;
  roundTitle: string;
  passRateStatistic: string;
  themeColor?: string;
}

export const WidescreenRoundSplash: React.FC<WidescreenRoundSplashProps> = ({
  roundNumber,
  roundTitle,
  passRateStatistic,
  themeColor = "#00E5FF",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Cinematic slow zoom-in from scale 0.95 to 1.05
  const scale = interpolate(frame, [0, fps * 4], [0.95, 1.05], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Opacity fade in (0-15 frames) and fade out (last 15 frames)
  const opacity = interpolate(
    frame,
    [0, 15, fps * 4 - 15, fps * 4],
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
        }}
      >
        {/* Round Tag */}
        <div
          style={{
            fontFamily: "system-ui, sans-serif",
            fontSize: 22,
            fontWeight: 800,
            letterSpacing: "0.2em",
            color: themeColor,
            textTransform: "uppercase",
            marginBottom: 16,
            padding: "8px 24px",
            borderRadius: 30,
            backgroundColor: "rgba(0, 229, 255, 0.1)",
            border: `1px solid ${themeColor}`,
            boxShadow: `0 0 20px ${themeColor}40`,
          }}
        >
          ROUND {String(roundNumber).padStart(2, "0")}
        </div>

        {/* Big Splash Title */}
        <div
          style={{
            fontFamily: "system-ui, -apple-system, sans-serif",
            fontSize: 64,
            fontWeight: 900,
            letterSpacing: "0.06em",
            color: "#FFFFFF",
            textTransform: "uppercase",
            textAlign: "center",
            maxWidth: 1400,
            marginBottom: 24,
            textShadow: "0 4px 20px rgba(0, 0, 0, 0.8)",
          }}
        >
          {roundTitle}
        </div>

        {/* Pass rate callout */}
        <div
          style={{
            fontFamily: "system-ui, sans-serif",
            fontSize: 28,
            fontWeight: 600,
            letterSpacing: "0.1em",
            color: "#8B949E",
            textTransform: "uppercase",
          }}
        >
          {passRateStatistic} &nbsp;|&nbsp; <span style={{ color: "#FFFFFF" }}>GET READY!</span>
        </div>
      </div>
    </div>
  );
};

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
  themeColor = "#00F0FF",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Cinematic slow zoom-in from scale 0.95 to 1.05
  const scale = interpolate(frame, [0, fps * 4], [0.94, 1.06], {
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
        background: "radial-gradient(circle at center, #141C26 0%, #05070A 100%)",
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
            fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
            fontSize: 22,
            fontWeight: 900,
            letterSpacing: "0.22em",
            color: themeColor,
            textTransform: "uppercase",
            marginBottom: 20,
            padding: "10px 30px",
            borderRadius: 30,
            backgroundColor: "rgba(0, 240, 255, 0.1)",
            border: `1.5px solid ${themeColor}`,
            boxShadow: `0 0 25px ${themeColor}50, inset 0 1px 1px rgba(255, 255, 255, 0.2)`,
            textShadow: `0 0 14px ${themeColor}`,
          }}
        >
          ROUND {String(roundNumber).padStart(2, "0")}
        </div>

        {/* Big Splash Title */}
        <div
          style={{
            fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
            fontSize: 66,
            fontWeight: 900,
            letterSpacing: "0.05em",
            color: "#FFFFFF",
            textTransform: "uppercase",
            textAlign: "center",
            maxWidth: 1500,
            marginBottom: 24,
            textShadow: `0 0 35px ${themeColor}60, 0 6px 24px rgba(0, 0, 0, 0.9)`,
            WebkitTextStroke: "1px rgba(0, 0, 0, 0.7)",
          }}
        >
          {roundTitle}
        </div>

        {/* Pass rate callout in English */}
        <div
          style={{
            fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
            fontSize: 24,
            fontWeight: 800,
            letterSpacing: "0.12em",
            color: "#94A3B8",
            textTransform: "uppercase",
            textShadow: "0 2px 6px rgba(0, 0, 0, 0.9)",
          }}
        >
          {passRateStatistic} &nbsp;|&nbsp; <span style={{ color: "#00F0FF", textShadow: "0 0 12px #00F0FF" }}>GET READY!</span>
        </div>
      </div>
    </div>
  );
};

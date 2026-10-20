import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

interface WidescreenRoundSplashProps {
  roundNumber: number;
  roundTitle: string;
  passRateStatistic: string;
  themeColor?: string;
  relativeFrame?: number;
  durationFrames?: number;
}

export const WidescreenRoundSplash: React.FC<WidescreenRoundSplashProps> = ({
  roundNumber,
  roundTitle,
  passRateStatistic,
  themeColor = "#00F0FF",
  relativeFrame,
  durationFrames,
}) => {
  const currentFrame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const frame = relativeFrame !== undefined ? relativeFrame : currentFrame;
  const duration = durationFrames ?? fps * 3;

  // Cinematic slow zoom-in from scale 0.95 to 1.05
  const scale = interpolate(frame, [0, duration], [0.94, 1.06], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Opacity fade in (0-15 frames) and fade out (last 15 frames)
  const opacity = interpolate(
    frame,
    [0, 15, duration - 15, duration],
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
        {/* Round Tag - Volumetric Yellow Pill */}
        <div
          style={{
            fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
            fontSize: 22,
            fontWeight: 900,
            letterSpacing: "0.15em",
            color: "#0F172A",
            textTransform: "uppercase",
            marginBottom: 24,
            padding: "12px 36px",
            borderRadius: 30,
            background: "linear-gradient(180deg, #FFE033 0%, #F59E0B 100%)",
            border: "2.5px solid #FEF08A",
            boxShadow: "0 12px 28px rgba(245, 158, 11, 0.45), 0 4px 12px rgba(0, 0, 0, 0.6), inset 0 2px 4px rgba(255, 255, 255, 0.8), inset 0 -2px 4px rgba(180, 83, 9, 0.4)",
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

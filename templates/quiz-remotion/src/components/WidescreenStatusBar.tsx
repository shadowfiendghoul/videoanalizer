import React from "react";
import { interpolate, spring } from "remotion";

interface WidescreenStatusBarProps {
  roundTitle: string;
  themeColor?: string;
  currentQuestionNumber: number;
  totalQuestionsInRound: number;
  relativeFrame?: number;
}

export const WidescreenStatusBar: React.FC<WidescreenStatusBarProps> = ({
  roundTitle,
  themeColor = "#00F0FF",
  currentQuestionNumber,
  totalQuestionsInRound,
  relativeFrame = 60,
}) => {
  const currentFormatted = String(currentQuestionNumber).padStart(2, "0");
  const totalFormatted = String(totalQuestionsInRound).padStart(2, "0");

  const entrance = spring({
    frame: relativeFrame,
    fps: 60,
    config: { damping: 14, mass: 0.7, stiffness: 120 },
  });
  const translateY = interpolate(entrance, [0, 1], [-40, 0]);
  const opacity = interpolate(relativeFrame, [0, 6], [0.4, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <>
      {/* Top-Left Round Badge (X: 120px, Y: 50px, W: 500px, H: 64px) */}
      <div
        style={{
          position: "absolute",
          left: 120,
          top: 50,
          width: 500,
          height: 64,
          borderRadius: 16,
          background: "linear-gradient(180deg, #1C2430 0%, #0F141C 100%)",
          border: `1.5px solid rgba(255, 255, 255, 0.12)`,
          display: "flex",
          alignItems: "center",
          paddingLeft: 24,
          paddingRight: 24,
          boxShadow: `0 16px 36px rgba(0, 0, 0, 0.7), 0 0 24px ${themeColor}25, inset 0 1px 1px rgba(255, 255, 255, 0.25)`,
          transform: `translateY(${translateY}px)`,
          opacity,
          zIndex: 10,
        }}
      >
        <span
          style={{
            display: "inline-block",
            width: 12,
            height: 12,
            borderRadius: "50%",
            backgroundColor: themeColor,
            marginRight: 16,
            boxShadow: `0 0 14px ${themeColor}, 0 0 24px ${themeColor}`,
          }}
        />
        <span
          style={{
            fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
            fontWeight: 900,
            fontSize: 22,
            textTransform: "uppercase",
            color: themeColor,
            letterSpacing: "0.06em",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            textShadow: `0 0 16px ${themeColor}88, 0 2px 4px rgba(0, 0, 0, 0.95)`,
          }}
        >
          {roundTitle}
        </span>
      </div>

      {/* Top-Right Question Tracker (X: 1460px, Y: 50px, W: 340px, H: 64px) */}
      <div
        style={{
          position: "absolute",
          left: 1460,
          top: 50,
          width: 340,
          height: 64,
          borderRadius: 16,
          background: "linear-gradient(180deg, #1C2430 0%, #0F141C 100%)",
          border: "1.5px solid rgba(255, 255, 255, 0.12)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 16px 36px rgba(0, 0, 0, 0.7), 0 0 24px rgba(0, 240, 255, 0.15), inset 0 1px 1px rgba(255, 255, 255, 0.25)",
          transform: `translateY(${translateY}px)`,
          opacity,
          zIndex: 10,
        }}
      >
        <span
          style={{
            fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
            fontWeight: 800,
            fontSize: 22,
            letterSpacing: "0.1em",
            color: "#94A3B8",
            textShadow: "0 2px 4px rgba(0, 0, 0, 0.8)",
          }}
        >
          QUESTION{" "}
          <span
            style={{
              color: "#FFFFFF",
              fontWeight: 900,
              fontSize: 26,
              textShadow: "0 0 16px rgba(255, 255, 255, 0.8), 0 2px 6px rgba(0, 0, 0, 0.95)",
            }}
          >
            {currentFormatted}
          </span>
          <span style={{ color: "#64748B", margin: "0 4px" }}>/</span>
          <span style={{ color: "#94A3B8", fontWeight: 800 }}>{totalFormatted}</span>
        </span>
      </div>
    </>
  );
};

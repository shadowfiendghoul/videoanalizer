import React from "react";
import { interpolate, spring } from "remotion";

interface WidescreenStatusBarProps {
  roundTitle: string;
  themeColor?: string;
  currentQuestionNumber: number;
  totalQuestionsInRound?: number;
  totalQuestions?: number;
  relativeFrame?: number;
}

export const WidescreenStatusBar: React.FC<WidescreenStatusBarProps> = ({
  roundTitle,
  themeColor = "#00F0FF",
  currentQuestionNumber,
  totalQuestionsInRound,
  totalQuestions,
  relativeFrame = 60,
}) => {
  const total = totalQuestions ?? totalQuestionsInRound ?? 50;
  const currentFormatted = String(currentQuestionNumber).padStart(2, "0");
  const totalFormatted = String(total).padStart(2, "0");

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
      {/* Top-Left Round Badge (Volumetric Yellow Gaming Pill) */}
      <div
        style={{
          position: "absolute",
          left: 120,
          top: 46,
          minWidth: 420,
          maxWidth: 620,
          height: 68,
          borderRadius: 34,
          background: "linear-gradient(180deg, #FFE033 0%, #F59E0B 100%)",
          border: "2.5px solid #FEF08A",
          display: "flex",
          alignItems: "center",
          paddingLeft: 26,
          paddingRight: 28,
          boxShadow: "0 14px 32px rgba(245, 158, 11, 0.45), 0 4px 14px rgba(0, 0, 0, 0.6), inset 0 2px 4px rgba(255, 255, 255, 0.8), inset 0 -3px 4px rgba(180, 83, 9, 0.4)",
          transform: `translateY(${translateY}px)`,
          opacity,
          zIndex: 10,
        }}
      >
        <span
          style={{
            display: "inline-block",
            width: 14,
            height: 14,
            borderRadius: "50%",
            backgroundColor: "#0F172A",
            marginRight: 16,
            boxShadow: "0 0 8px rgba(0, 0, 0, 0.35)",
            flexShrink: 0,
          }}
        />
        <span
          style={{
            fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
            fontWeight: 900,
            fontSize: 22,
            textTransform: "uppercase",
            color: "#0F172A",
            letterSpacing: "0.06em",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            textShadow: "0 1px 1px rgba(255, 255, 255, 0.4)",
          }}
        >
          {roundTitle}
        </span>
      </div>

      {/* Top-Right Question/Total Counter (Volumetric Magenta-Pink Gaming Pill) */}
      <div
        style={{
          position: "absolute",
          left: 1440,
          top: 46,
          width: 360,
          height: 68,
          borderRadius: 34,
          background: "linear-gradient(180deg, #F43F5E 0%, #D946EF 55%, #C026D3 100%)",
          border: "2.5px solid rgba(255, 255, 255, 0.6)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 14px 32px rgba(244, 63, 94, 0.45), 0 4px 14px rgba(0, 0, 0, 0.6), inset 0 2px 4px rgba(255, 255, 255, 0.75), inset 0 -3px 4px rgba(134, 25, 143, 0.4)",
          transform: `translateY(${translateY}px)`,
          opacity,
          zIndex: 10,
        }}
      >
        <span
          style={{
            fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
            fontWeight: 800,
            fontSize: 20,
            letterSpacing: "0.1em",
            color: "rgba(255, 255, 255, 0.95)",
            textShadow: "0 2px 4px rgba(0, 0, 0, 0.4)",
          }}
        >
          TOTAL{" "}
          <span
            style={{
              color: "#FFFFFF",
              fontWeight: 900,
              fontSize: 26,
              textShadow: "0 2px 8px rgba(0, 0, 0, 0.5)",
            }}
          >
            {currentFormatted}
          </span>
          <span style={{ color: "rgba(255, 255, 255, 0.7)", margin: "0 4px", fontSize: 22 }}>/</span>
          <span style={{ color: "rgba(255, 255, 255, 0.95)", fontWeight: 800, fontSize: 22 }}>{totalFormatted}</span>
        </span>
      </div>
    </>
  );
};

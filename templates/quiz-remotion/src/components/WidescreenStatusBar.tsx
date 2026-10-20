import React from "react";
import { interpolate, spring } from "remotion";

interface WidescreenStatusBarProps {
  roundNumber: number;
  currentQuestionInRound: number;
  totalQuestionsInRound: number;
  globalQuestionNumber: number;
  totalQuestionsCount: number;
  containerLeft?: number;
  containerWidth?: number;
  relativeFrame?: number;
}

export const WidescreenStatusBar: React.FC<WidescreenStatusBarProps> = ({
  roundNumber = 1,
  currentQuestionInRound = 1,
  totalQuestionsInRound = 10,
  globalQuestionNumber = 1,
  totalQuestionsCount = 50,
  containerLeft = 230,
  containerWidth = 1460,
  relativeFrame = 60,
}) => {
  const entrance = spring({
    frame: relativeFrame,
    fps: 60,
    config: { damping: 14, mass: 0.7, stiffness: 120 },
  });
  const translateY = interpolate(entrance, [0, 1], [-25, 0]);
  const opacity = interpolate(relativeFrame, [0, 6], [0.4, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        left: containerLeft,
        top: 55,
        width: containerWidth,
        height: 52,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        transform: `translateY(${translateY}px)`,
        opacity,
        zIndex: 15,
      }}
    >
      {/* Left: [ ROUND X ] X/10 */}
      <div style={{ display: "flex", alignItems: "center" }}>
        <div
          style={{
            backgroundColor: "#FFA500",
            borderRadius: 9999,
            padding: "8px 24px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 4px 14px rgba(0, 0, 0, 0.4)",
          }}
        >
          <span
            style={{
              fontFamily: "'Montserrat', 'Inter Tight', 'Arial Black', sans-serif",
              fontWeight: 900,
              fontSize: 26,
              color: "#FFFFFF",
              letterSpacing: "0.05em",
              textTransform: "uppercase",
              lineHeight: 1,
            }}
          >
            ROUND {roundNumber}
          </span>
        </div>

        <span
          style={{
            fontFamily: "'Montserrat', 'Inter Tight', 'Arial Black', sans-serif",
            fontWeight: 900,
            fontSize: 34,
            color: "#FFA500",
            marginLeft: 18,
            letterSpacing: "0.03em",
            textShadow: "0 2px 6px rgba(0, 0, 0, 0.6)",
            lineHeight: 1,
          }}
        >
          {currentQuestionInRound}/{totalQuestionsInRound}
        </span>
      </div>

      {/* Right: [ TOTAL ] X/50 */}
      <div style={{ display: "flex", alignItems: "center" }}>
        <div
          style={{
            backgroundColor: "#FFFFFF",
            borderRadius: 9999,
            padding: "8px 26px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 4px 14px rgba(0, 0, 0, 0.4)",
          }}
        >
          <span
            style={{
              fontFamily: "'Montserrat', 'Inter Tight', 'Arial Black', sans-serif",
              fontWeight: 900,
              fontSize: 26,
              color: "#E6007A",
              letterSpacing: "0.07em",
              textTransform: "uppercase",
              lineHeight: 1,
            }}
          >
            TOTAL
          </span>
        </div>

        <span
          style={{
            fontFamily: "'Montserrat', 'Inter Tight', 'Arial Black', sans-serif",
            fontWeight: 900,
            fontSize: 34,
            color: "#FFFFFF",
            marginLeft: 18,
            letterSpacing: "0.03em",
            textShadow: "0 2px 6px rgba(0, 0, 0, 0.6)",
            lineHeight: 1,
          }}
        >
          {globalQuestionNumber}/{totalQuestionsCount}
        </span>
      </div>
    </div>
  );
};

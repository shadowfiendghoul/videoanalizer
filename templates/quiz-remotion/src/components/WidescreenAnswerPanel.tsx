import React from "react";
import { spring, useVideoConfig } from "remotion";

interface WidescreenAnswerPanelProps {
  answerText: string;
  relativeFrame: number;
  revealFrame?: number; // default 360 frames (6.0s at 60fps)
}

export const WidescreenAnswerPanel: React.FC<WidescreenAnswerPanelProps> = ({
  answerText,
  relativeFrame,
  revealFrame = 360,
}) => {
  const { fps } = useVideoConfig();

  const isRevealed = relativeFrame >= revealFrame;

  // Spring bounce scale animation starting at revealFrame
  const scale = isRevealed
    ? spring({
        frame: relativeFrame - revealFrame,
        fps,
        config: {
          damping: 12,
          mass: 0.5,
          stiffness: 220,
        },
      })
    : 0;

  // Dynamic font size scaling for long answer titles (>30 characters)
  const textLength = answerText.length;
  let fontSize = 42;
  if (textLength > 40) {
    fontSize = 24;
  } else if (textLength > 30) {
    fontSize = 30;
  } else if (textLength > 20) {
    fontSize = 36;
  }

  if (!isRevealed) {
    return null;
  }

  return (
    <div
      style={{
        position: "absolute",
        left: 360,
        top: 760,
        width: 1200,
        height: 96,
        borderRadius: 24,
        background: "linear-gradient(135deg, #10B981 0%, #047857 100%)",
        border: "3px solid #FFFFFF",
        boxShadow: "0 20px 50px rgba(0, 0, 0, 0.85), 0 0 45px rgba(16, 185, 129, 0.65)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transform: `scale(${scale})`,
        zIndex: 30,
        paddingLeft: 36,
        paddingRight: 36,
      }}
    >
      <span
        style={{
          fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
          fontSize,
          fontWeight: 900,
          letterSpacing: "0.06em",
          color: "#FFFFFF",
          textTransform: "uppercase",
          textAlign: "center",
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
          textShadow: "0 4px 12px rgba(0, 0, 0, 0.5), 0 0 16px rgba(255, 255, 255, 0.3)",
        }}
      >
        {answerText}
      </span>
    </div>
  );
};

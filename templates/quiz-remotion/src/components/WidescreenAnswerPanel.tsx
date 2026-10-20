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
    return (
      <div
        style={{
          position: "absolute",
          left: 460,
          top: 855,
          width: 1000,
          height: 90,
          borderRadius: 18,
          background: "linear-gradient(180deg, #141A23 0%, #0A0D12 100%)",
          border: "1.5px dashed rgba(255, 255, 255, 0.15)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 10px 30px rgba(0, 0, 0, 0.6), inset 0 2px 4px rgba(0, 0, 0, 0.5)",
          zIndex: 10,
        }}
      >
        <span
          style={{
            fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
            fontSize: 20,
            fontWeight: 800,
            letterSpacing: "0.2em",
            color: "#475569",
            textTransform: "uppercase",
            textShadow: "0 2px 4px rgba(0, 0, 0, 0.8)",
          }}
        >
          ● &nbsp; ● &nbsp; ● &nbsp; WAITING FOR ANSWER &nbsp; ● &nbsp; ● &nbsp; ●
        </span>
      </div>
    );
  }

  return (
    <div
      style={{
        position: "absolute",
        left: 460,
        top: 855,
        width: 1000,
        height: 90,
        borderRadius: 18,
        background: "linear-gradient(135deg, #10B981 0%, #047857 100%)",
        border: "2px solid rgba(255, 255, 255, 0.45)",
        boxShadow: "0 20px 50px rgba(0, 0, 0, 0.8), 0 0 45px rgba(16, 185, 129, 0.6), inset 0 2px 3px rgba(255, 255, 255, 0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transform: `scale(${scale})`,
        zIndex: 10,
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

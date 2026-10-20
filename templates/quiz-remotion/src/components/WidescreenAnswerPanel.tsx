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

  // If before reveal frame, display nothing or subtle prompt
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
  let fontSize = 44;
  if (textLength > 40) {
    fontSize = 26;
  } else if (textLength > 30) {
    fontSize = 32;
  } else if (textLength > 20) {
    fontSize = 38;
  }

  if (!isRevealed) {
    return (
      <div
        style={{
          position: "absolute",
          left: 460,
          top: 860,
          width: 1000,
          height: 90,
          borderRadius: 16,
          backgroundColor: "#161B22",
          border: "1px dashed #30363D",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 10,
        }}
      >
        <span
          style={{
            fontFamily: "system-ui, sans-serif",
            fontSize: 22,
            fontWeight: 700,
            letterSpacing: "0.15em",
            color: "#484F58",
            textTransform: "uppercase",
          }}
        >
          ● ● ●
        </span>
      </div>
    );
  }

  return (
    <div
      style={{
        position: "absolute",
        left: 460,
        top: 860,
        width: 1000,
        height: 90,
        borderRadius: 16,
        backgroundColor: "#10B981",
        boxShadow: "0 10px 30px rgba(16, 185, 129, 0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transform: `scale(${scale})`,
        zIndex: 10,
        paddingLeft: 30,
        paddingRight: 30,
      }}
    >
      <span
        style={{
          fontFamily: "system-ui, -apple-system, sans-serif",
          fontSize,
          fontWeight: 900,
          letterSpacing: "0.06em",
          color: "#FFFFFF",
          textTransform: "uppercase",
          textAlign: "center",
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
          textShadow: "0 2px 4px rgba(0, 0, 0, 0.3)",
        }}
      >
        {answerText}
      </span>
    </div>
  );
};

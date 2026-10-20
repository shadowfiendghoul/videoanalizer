import React from "react";

interface WidescreenStatusBarProps {
  roundTitle: string;
  themeColor?: string;
  currentQuestionNumber: number;
  totalQuestionsInRound: number;
}

export const WidescreenStatusBar: React.FC<WidescreenStatusBarProps> = ({
  roundTitle,
  themeColor = "#58A6FF",
  currentQuestionNumber,
  totalQuestionsInRound,
}) => {
  const currentFormatted = String(currentQuestionNumber).padStart(2, "0");
  const totalFormatted = String(totalQuestionsInRound).padStart(2, "0");

  return (
    <>
      {/* Top-Left Round Badge (X: 120px, Y: 50px, W: 480px, H: 60px) */}
      <div
        style={{
          position: "absolute",
          left: 120,
          top: 50,
          width: 480,
          height: 60,
          borderRadius: 14,
          backgroundColor: "#161B22",
          border: "1px solid #30363D",
          display: "flex",
          alignItems: "center",
          paddingLeft: 24,
          paddingRight: 24,
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.4)",
          zIndex: 10,
        }}
      >
        <span
          style={{
            display: "inline-block",
            width: 10,
            height: 10,
            borderRadius: "50%",
            backgroundColor: themeColor,
            marginRight: 14,
            boxShadow: `0 0 10px ${themeColor}`,
          }}
        />
        <span
          style={{
            fontFamily: "system-ui, -apple-system, sans-serif",
            fontWeight: 700,
            fontSize: 24,
            textTransform: "uppercase",
            color: themeColor,
            letterSpacing: "0.05em",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {roundTitle}
        </span>
      </div>

      {/* Top-Right Question Tracker (X: 1480px, Y: 50px, W: 320px, H: 60px) */}
      <div
        style={{
          position: "absolute",
          left: 1480,
          top: 50,
          width: 320,
          height: 60,
          borderRadius: 14,
          backgroundColor: "#161B22",
          border: "1px solid #30363D",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.4)",
          zIndex: 10,
        }}
      >
        <span
          style={{
            fontFamily: "system-ui, -apple-system, sans-serif",
            fontWeight: 700,
            fontSize: 24,
            letterSpacing: "0.08em",
            color: "#8B949E",
          }}
        >
          QUESTION{" "}
          <span style={{ color: "#FFFFFF" }}>{currentFormatted}</span>
          {" / "}
          <span>{totalFormatted}</span>
        </span>
      </div>
    </>
  );
};

import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { WidescreenScoreTier } from "../types";

interface WidescreenOutroProps {
  scoreTiers: WidescreenScoreTier[];
  callToAction: string;
}

export const WidescreenOutro: React.FC<WidescreenOutroProps> = ({
  scoreTiers,
  callToAction,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Gentle fade-in
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        top: 0,
        width: 1920,
        height: 1080,
        backgroundColor: "#0D1117",
        background: "radial-gradient(circle at center, #151D29 0%, #06090D 100%)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        opacity,
        zIndex: 20,
        padding: 60,
      }}
    >
      {/* Title */}
      <div
        style={{
          fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
          fontSize: 50,
          fontWeight: 900,
          color: "#FFFFFF",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          marginBottom: 48,
          textShadow: "0 0 35px rgba(0, 240, 255, 0.5), 0 4px 16px rgba(0, 0, 0, 0.9)",
          WebkitTextStroke: "1px rgba(0, 0, 0, 0.7)",
        }}
      >
        SCORE EVALUATION
      </div>

      {/* 4 Score Tier Cards */}
      <div
        style={{
          display: "flex",
          gap: 24,
          marginBottom: 56,
        }}
      >
        {scoreTiers.map((tier, idx) => {
          // Staggered card appearance (frames 20, 35, 50, 65)
          const cardOpacity = interpolate(
            frame,
            [20 + idx * 15, 35 + idx * 15],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );
          const cardY = interpolate(
            frame,
            [20 + idx * 15, 35 + idx * 15],
            [30, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );

          return (
            <div
              key={`tier_${idx}`}
              style={{
                width: 320,
                height: 220,
                borderRadius: 20,
                background: "linear-gradient(180deg, #1C2430 0%, #0F141C 100%)",
                border: `2px solid ${tier.badge_color}66`,
                boxShadow: `0 16px 40px rgba(0, 0, 0, 0.7), 0 0 25px ${tier.badge_color}30, inset 0 1px 1px rgba(255, 255, 255, 0.2)`,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: 20,
                opacity: cardOpacity,
                transform: `translateY(${cardY}px)`,
              }}
            >
              <div
                style={{
                  fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
                  fontSize: 30,
                  fontWeight: 900,
                  color: tier.badge_color,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  marginBottom: 14,
                  textShadow: `0 0 16px ${tier.badge_color}99`,
                }}
              >
                {tier.tier_name}
              </div>
              <div
                style={{
                  fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
                  fontSize: 24,
                  fontWeight: 800,
                  color: "#FFFFFF",
                  letterSpacing: "0.06em",
                  textShadow: "0 2px 4px rgba(0, 0, 0, 0.9)",
                }}
              >
                {tier.min_score} – {tier.max_score} PTS
              </div>
            </div>
          );
        })}
      </div>

      {/* Call to action footer banner */}
      <div
        style={{
          fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
          fontSize: 28,
          fontWeight: 900,
          letterSpacing: "0.1em",
          color: "#00F0FF",
          textTransform: "uppercase",
          padding: "16px 48px",
          borderRadius: 36,
          backgroundColor: "rgba(0, 240, 255, 0.1)",
          border: "2px solid #00F0FF",
          boxShadow: "0 0 30px rgba(0, 240, 255, 0.4), inset 0 1px 2px rgba(255, 255, 255, 0.3)",
          textShadow: "0 0 16px #00F0FF",
        }}
      >
        {callToAction}
      </div>
    </div>
  );
};

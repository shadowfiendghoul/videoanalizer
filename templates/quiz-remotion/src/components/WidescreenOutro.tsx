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
          fontFamily: "system-ui, -apple-system, sans-serif",
          fontSize: 48,
          fontWeight: 900,
          color: "#FFFFFF",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          marginBottom: 48,
          textShadow: "0 0 30px rgba(0, 229, 255, 0.4)",
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
          const cardDelay = idx * 10;
          const cardScale = interpolate(frame, [cardDelay, cardDelay + 15], [0.8, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const cardOpacity = interpolate(frame, [cardDelay, cardDelay + 15], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });

          return (
            <div
              key={idx}
              style={{
                width: 260,
                padding: "32px 20px",
                borderRadius: 18,
                backgroundColor: "#161B22",
                border: `2px solid ${tier.badge_color || "#30363D"}`,
                boxShadow: `0 8px 24px ${tier.badge_color}30`,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                transform: `scale(${cardScale})`,
                opacity: cardOpacity,
              }}
            >
              <div
                style={{
                  fontFamily: "system-ui, sans-serif",
                  fontSize: 22,
                  fontWeight: 800,
                  color: tier.badge_color,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  marginBottom: 12,
                }}
              >
                {tier.tier_name}
              </div>
              <div
                style={{
                  fontFamily: "system-ui, sans-serif",
                  fontSize: 36,
                  fontWeight: 900,
                  color: "#FFFFFF",
                }}
              >
                {tier.min_score}–{tier.max_score}
              </div>
              <div
                style={{
                  fontSize: 14,
                  fontWeight: 600,
                  color: "#8B949E",
                  marginTop: 6,
                  textTransform: "uppercase",
                }}
              >
                POINTS
              </div>
            </div>
          );
        })}
      </div>

      {/* Call to Action Banner */}
      <div
        style={{
          padding: "18px 48px",
          borderRadius: 40,
          backgroundColor: "#10B981",
          boxShadow: "0 0 30px rgba(16, 185, 129, 0.4)",
          fontFamily: "system-ui, sans-serif",
          fontSize: 28,
          fontWeight: 800,
          color: "#FFFFFF",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
        }}
      >
        {callToAction}
      </div>
    </div>
  );
};

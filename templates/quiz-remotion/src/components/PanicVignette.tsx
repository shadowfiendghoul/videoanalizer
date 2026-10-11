import React from "react";

interface PanicVignetteProps {
  currentFrame: number;
  active: boolean;
  intensity?: number;
}

export const PanicVignette: React.FC<PanicVignetteProps> = ({
  currentFrame,
  active,
  intensity = 0.65,
}) => {
  if (!active) {
    return null;
  }

  // Heartbeat pulse calculation (~175 BPM -> 20 frames cycle at 60fps)
  const pulse = (Math.sin(currentFrame * 0.32) + 1) / 2; // 0..1
  const opacity = Math.min(1.0, 0.25 + pulse * intensity);

  return (
    <div
      style={{
        opacity,
        background:
          "radial-gradient(circle at center, transparent 40%, rgba(239, 68, 68, 0.45) 85%, rgba(185, 28, 28, 0.85) 100%)",
        boxShadow: "inset 0 0 100px rgba(239, 68, 68, 0.6)",
      }}
      className="absolute inset-0 pointer-events-none z-20 transition-opacity duration-100"
    />
  );
};

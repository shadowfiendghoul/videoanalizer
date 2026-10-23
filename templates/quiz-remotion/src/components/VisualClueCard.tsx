import React from "react";
import { Img, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { resolveAssetUrl } from "../utils/assets";

interface VisualClueCardProps {
  imagePath: string;
  themeColor: string;
  questionNumber: number;
  answerText?: string;
  revealOffset?: number;
}

export const VisualClueCard: React.FC<VisualClueCardProps> = ({
  imagePath,
  themeColor,
  questionNumber,
  answerText,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Energetic bouncy entrance spring when the answer is revealed
  const entrance = spring({
    frame,
    fps,
    config: {
      damping: 12,
      mass: 0.6,
      stiffness: 110,
    },
  });

  // Subtle breathing float animation
  const floatY = Math.sin(frame * 0.08) * 3;
  const resolvedUrl = resolveAssetUrl(imagePath);

  return (
    <div
      className="absolute right-12 top-[50%] -translate-y-1/2 z-25 flex items-center justify-center pointer-events-none"
      style={{
        transform: `translateY(calc(-50% + ${floatY}px)) scale(${entrance})`,
        transformOrigin: "center center",
        width: 540,
        height: 540,
      }}
    >
      <Img
        src={resolvedUrl}
        className="max-w-full max-h-full object-contain"
        style={{
          filter: "drop-shadow(0 24px 45px rgba(0, 0, 0, 0.95)) drop-shadow(0 4px 12px rgba(0, 0, 0, 0.85))",
        }}
      />
    </div>
  );
};

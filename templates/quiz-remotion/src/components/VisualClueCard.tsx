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
      className="absolute right-10 top-[51%] -translate-y-1/2 z-25 flex flex-col items-center pointer-events-none"
      style={{
        transform: `translateY(calc(-50% + ${floatY}px)) scale(${entrance})`,
        transformOrigin: "center center",
      }}
    >
      <div
        className="w-[490px] h-[490px] rounded-[36px] p-4 backdrop-blur-2xl flex flex-col items-center justify-center relative overflow-hidden shadow-2xl"
        style={{
          background: "linear-gradient(145deg, rgba(15, 23, 42, 0.94) 0%, rgba(9, 14, 26, 0.96) 100%)",
          boxShadow: "0 30px 70px rgba(0, 0, 0, 0.85), 0 0 45px rgba(34, 197, 94, 0.35)",
        }}
      >
        {/* Ambient emerald glow behind the card */}
        <div
          className="absolute -top-16 -right-16 w-56 h-56 rounded-full blur-3xl opacity-35 pointer-events-none"
          style={{ backgroundColor: "#22C55E" }}
        />

        {/* Top-left answer indicator badge */}
        <div className="absolute top-4 left-4 z-10 flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-emerald-500 text-white font-black text-sm tracking-wider uppercase shadow-xl">
          <span>✓</span>
          <span>ОТВЕТ #{questionNumber}</span>
        </div>

        {/* Image display container (Clean borderless floating image) */}
        <div className="w-full h-full rounded-2xl flex items-center justify-center overflow-hidden p-3">
          <Img
            src={resolvedUrl}
            className="w-full h-full object-contain drop-shadow-[0_20px_35px_rgba(0,0,0,0.85)] filter"
          />
        </div>

        {/* Bottom answer name pill */}
        {answerText && (
          <div className="absolute bottom-4 left-4 right-4 z-10 flex items-center justify-center px-4 py-2.5 rounded-2xl bg-black/85 backdrop-blur-md shadow-2xl">
            <span
              className="text-white font-black text-xl tracking-wide uppercase truncate text-center drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)]"
              style={{ maxWidth: "420px" }}
            >
              {answerText}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

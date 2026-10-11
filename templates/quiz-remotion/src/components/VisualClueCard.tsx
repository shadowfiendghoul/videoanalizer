import React from "react";
import { Img, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { resolveAssetUrl } from "../utils/assets";

interface VisualClueCardProps {
  imagePath: string;
  themeColor: string;
  questionNumber: number;
  revealOffset: number;
}

export const VisualClueCard: React.FC<VisualClueCardProps> = ({
  imagePath,
  themeColor,
  questionNumber,
  revealOffset,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Smooth bouncy spring entrance when the question cue starts
  const entrance = spring({
    frame,
    fps,
    config: {
      damping: 14,
      mass: 0.6,
      stiffness: 130,
    },
  });

  const isRevealed = frame >= revealOffset;
  const revealProgress = isRevealed
    ? spring({
        frame: frame - revealOffset,
        fps,
        config: {
          damping: 12,
          mass: 0.5,
          stiffness: 150,
        },
      })
    : 0;

  // Subtle breathing float animation during the thinking phase
  const floatY = Math.sin(frame * 0.08) * 4;
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
        className="w-[490px] h-[490px] rounded-[32px] p-3.5 backdrop-blur-2xl border-2 flex flex-col items-center justify-center relative overflow-hidden shadow-2xl"
        style={{
          backgroundColor: "rgba(10, 15, 29, 0.88)",
          borderColor: isRevealed ? "#22C55E" : `${themeColor}99`,
          boxShadow: isRevealed
            ? "0 25px 60px rgba(0, 0, 0, 0.85), 0 0 35px rgba(34, 197, 94, 0.45)"
            : `0 25px 60px rgba(0, 0, 0, 0.85), 0 0 30px ${themeColor}33`,
        }}
      >
        {/* Ambient colored glow behind the card */}
        <div
          className="absolute -top-16 -right-16 w-44 h-44 rounded-full blur-3xl opacity-30 pointer-events-none"
          style={{ backgroundColor: themeColor }}
        />

        {/* Top-left question indicator badge */}
        <div className="absolute top-4 left-4 z-10 flex items-center gap-1.5 px-3 py-1 rounded-xl bg-black/75 backdrop-blur-md border border-white/20">
          <span className="text-sm">🔍</span>
          <span className="text-[13px] font-black tracking-wider uppercase text-white/90">
            Вопрос #{questionNumber}
          </span>
        </div>

        {/* Image display container */}
        <div className="w-full h-full rounded-2xl bg-black/40 border border-white/10 flex items-center justify-center overflow-hidden p-2">
          <Img
            src={resolvedUrl}
            className="w-full h-full object-contain drop-shadow-2xl rounded-xl"
          />
        </div>

        {/* Reveal confirmation badge overlay */}
        {isRevealed && (
          <div
            className="absolute bottom-4 right-4 z-10 flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-emerald-600/95 text-white font-black text-xs tracking-wider uppercase border border-white/40 shadow-xl"
            style={{
              transform: `scale(${revealProgress})`,
              transformOrigin: "bottom right",
            }}
          >
            <span>✓</span>
            <span>ОТВЕТ</span>
          </div>
        )}
      </div>
    </div>
  );
};

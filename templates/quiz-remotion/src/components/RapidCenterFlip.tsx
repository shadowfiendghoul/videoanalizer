import React from "react";
import { useCurrentFrame, staticFile, Img } from "remotion";
import { VisualQuizItem } from "../types";

interface RapidCenterFlipProps {
  items: VisualQuizItem[];
  hookEndFrame: number;
  flipIntervalMs?: number;
}

export const RapidCenterFlip: React.FC<RapidCenterFlipProps> = ({
  items,
  hookEndFrame,
  flipIntervalMs = 120,
}) => {
  const frame = useCurrentFrame();

  if (frame >= hookEndFrame || items.length === 0) {
    return null;
  }

  // At 60fps, 120ms is ~7.2 frames
  const framesPerFlip = Math.max(1, Math.round(60 * (flipIntervalMs / 1000)));
  const activeIndex = Math.floor(frame / framesPerFlip) % items.length;
  const currentItem = items[activeIndex];

  const imageSrc = currentItem?.image_path
    ? staticFile(currentItem.image_path)
    : currentItem?.image_url || "";

  return (
    <div
      style={{
        position: "absolute",
        left: 560,
        top: 260,
        width: 380,
        height: 380,
      }}
      className="rounded-3xl border-4 border-cyan-400/80 bg-slate-900/90 shadow-[0_0_35px_rgba(6,182,212,0.4)] flex items-center justify-center overflow-hidden p-3 z-20"
    >
      {imageSrc ? (
        <Img
          src={imageSrc}
          className="w-full h-full object-contain"
        />
      ) : (
        <span className="text-6xl font-black text-cyan-400">?</span>
      )}
    </div>
  );
};

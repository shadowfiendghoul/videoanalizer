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
        left: 550,
        top: 220,
        width: 440,
        height: 440,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        filter: "drop-shadow(0 12px 24px rgba(0,0,0,0.65))",
      }}
      className="z-20 pointer-events-none select-none"
    >
      {imageSrc ? (
        <Img
          src={imageSrc}
          className="max-w-full max-h-full object-contain"
          onError={(e) => {
            console.warn("Failed to load rapid flip image:", imageSrc, e);
          }}
        />
      ) : (
        <span
          className="text-8xl font-black text-white"
          style={{
            WebkitTextStroke: "3px black",
            textShadow: "3px 3px 0 #000, -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000",
          }}
        >
          ?
        </span>
      )}
    </div>
  );
};

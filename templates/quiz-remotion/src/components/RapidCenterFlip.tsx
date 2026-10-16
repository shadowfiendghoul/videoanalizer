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

  // Pace flips so ~7 logos flash over the 3.0-3.2s hook window (0.42s per logo)
  const framesPerFlip = Math.max(1, Math.round(60 * 0.42));
  const activeIndex = Math.floor(frame / framesPerFlip) % items.length;
  const currentItem = items[activeIndex];

  const imageSrc = currentItem?.image_path
    ? staticFile(currentItem.image_path)
    : currentItem?.image_url || "";

  return (
    <div
      style={{
        position: "absolute",
        left: "50%",
        top: "44%",
        transform: "translate(-50%, -50%)",
        width: 580,
        height: 580,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        filter: "drop-shadow(0 16px 36px rgba(0,0,0,0.8))",
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
          className="text-9xl font-black text-white"
          style={{
            fontFamily: "'Rubik', sans-serif",
            paintOrder: "stroke fill",
            WebkitTextStroke: "4px black",
            textShadow: "0 10px 20px rgba(0,0,0,0.8)",
          }}
        >
          ?
        </span>
      )}
    </div>
  );
};

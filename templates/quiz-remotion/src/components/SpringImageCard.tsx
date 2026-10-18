import React from "react";
import { useCurrentFrame, staticFile, spring, Img } from "remotion";
import { VisualQuizItem, VisualQuizTimingSlot } from "../types";

interface SpringImageCardProps {
  items: VisualQuizItem[];
  timingSlots: VisualQuizTimingSlot[];
  hookEndFrame: number;
}

export const SpringImageCard: React.FC<SpringImageCardProps> = ({
  items,
  timingSlots,
  hookEndFrame,
}) => {
  const frame = useCurrentFrame();

  if (frame < hookEndFrame) {
    return null;
  }

  // Find active slot
  const currentSlot = timingSlots.find(
    (s) => frame >= s.start_frame && frame <= s.end_frame
  );

  if (!currentSlot) {
    return null;
  }

  const item = items.find((it) => it.id === currentSlot.question_id);
  if (!item) {
    return null;
  }

  const localFrame = frame - currentSlot.start_frame;
  const scale = spring({
    frame: localFrame,
    fps: 60,
    config: { damping: 12, stiffness: 200 },
  });

  const imageSrc = item.image_path
    ? staticFile(item.image_path)
    : item.image_url || "";

  return (
    <div
      style={{
        position: "absolute",
        left: 370,
        top: 300,
        width: 590,
        height: 590,
        transform: `scale(${scale})`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        filter: "drop-shadow(0 14px 28px rgba(0,0,0,0.75))",
      }}
      className="z-20 pointer-events-none select-none"
    >
      {imageSrc ? (
        <Img
          src={imageSrc}
          className="max-w-full max-h-full object-contain"
          onError={(e) => {
            console.warn("Failed to load spring image card:", imageSrc, e);
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

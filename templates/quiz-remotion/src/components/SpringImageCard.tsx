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
        left: 560,
        top: 260,
        width: 380,
        height: 380,
        transform: `scale(${scale})`,
      }}
      className="rounded-3xl border-4 border-emerald-400/80 bg-slate-900/90 shadow-[0_0_40px_rgba(34,197,94,0.4)] flex items-center justify-center overflow-hidden p-4 z-20"
    >
      {imageSrc ? (
        <Img
          src={imageSrc}
          className="w-full h-full object-contain drop-shadow-md"
        />
      ) : (
        <span className="text-7xl font-black text-emerald-400">?</span>
      )}
    </div>
  );
};

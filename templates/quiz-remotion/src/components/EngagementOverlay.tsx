import React from "react";
import { useCurrentFrame, spring } from "remotion";
import { VisualQuizInterstitial, VisualQuizTimingSlot } from "../types";

interface EngagementOverlayProps {
  interstitials: VisualQuizInterstitial[];
  timingSlots: VisualQuizTimingSlot[];
}

export const EngagementOverlay: React.FC<EngagementOverlayProps> = ({
  interstitials,
  timingSlots,
}) => {
  const frame = useCurrentFrame();

  for (const item of interstitials) {
    const prevSlot = timingSlots.find((s) => s.question_id === item.after_question);
    const nextSlot = timingSlots.find((s) => s.question_id === item.after_question + 1);

    if (prevSlot && nextSlot) {
      const startF = prevSlot.end_frame;
      const endF = nextSlot.start_frame;

      if (frame >= startF && frame < endF) {
        const localFrame = frame - startF;
        const scale = spring({
          frame: localFrame,
          fps: 60,
          config: { damping: 10, stiffness: 180 },
        });

        if (item.type === "comment_bait") {
          return (
            <div
              style={{
                position: "absolute",
                left: 545,
                top: 360,
                transform: `scale(${scale})`,
              }}
              className="z-30 bg-gradient-to-r from-pink-500 to-purple-600 rounded-2xl p-4 shadow-[0_0_40px_rgba(236,72,153,0.6)] flex items-center gap-3 border-2 border-white/40 max-w-[395px]"
            >
              <div className="w-12 h-12 rounded-full bg-white flex items-center justify-center text-2xl shadow-md shrink-0">
                💬
              </div>
              <div className="text-white font-black text-lg leading-tight">
                {item.tts_text}
              </div>
            </div>
          );
        }

        if (item.type === "share_bait") {
          return (
            <div
              style={{
                position: "absolute",
                left: 545,
                top: 360,
                transform: `scale(${scale})`,
              }}
              className="z-30 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-2xl p-4 shadow-[0_0_40px_rgba(6,182,212,0.6)] flex items-center gap-3 border-2 border-white/40 max-w-[395px]"
            >
              <div className="w-12 h-12 rounded-full bg-white flex items-center justify-center text-2xl shadow-md shrink-0">
                ↗️
              </div>
              <div className="text-white font-black text-lg leading-tight">
                {item.tts_text}
              </div>
            </div>
          );
        }
      }
    }
  }

  return null;
};

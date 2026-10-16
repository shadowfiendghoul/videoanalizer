import React from "react";
import { useCurrentFrame } from "remotion";
import { VisualQuizItem, VisualQuizTimingSlot } from "../types";

interface ProgressiveLadderProps {
  items: VisualQuizItem[];
  timingSlots: VisualQuizTimingSlot[];
  hookEndFrame: number;
}

const TIER_COLORS = {
  easy: "#00E676",    // Bright vibrant TikTok green
  medium: "#FFEB3B",  // Bright vibrant TikTok yellow
  hard: "#FF1744",    // Bright vibrant TikTok red
  master: "#FF4081",  // Bright vibrant TikTok pink/magenta
};

export const ProgressiveLadder: React.FC<ProgressiveLadderProps> = ({
  items,
  timingSlots,
  hookEndFrame,
}) => {
  const frame = useCurrentFrame();

  if (frame < hookEndFrame) {
    return null;
  }

  // Groups matching reference video
  const groups = [
    { title: "Лёгкий", color: TIER_COLORS.easy, ids: [1, 2, 3] },
    { title: "Средний", color: TIER_COLORS.medium, ids: [4, 5, 6] },
    { title: "Сложный", color: TIER_COLORS.hard, ids: [7, 8, 9] },
    { title: "Мастер", color: TIER_COLORS.master, ids: [10] },
  ];

  return (
    <div
      style={{
        position: "absolute",
        left: 80,
        top: 220,
        width: 480,
        display: "flex",
        flexDirection: "column",
        gap: 20,
      }}
      className="z-20 pointer-events-none select-none font-sans"
    >
      {groups.map((grp, gIdx) => (
        <div key={gIdx} className="flex flex-col gap-1">
          {/* Category Header */}
          <div
            className="text-[42px] font-black tracking-tight"
            style={{
              color: grp.color,
              WebkitTextStroke: "3px #000000",
              textShadow:
                "3px 3px 0 #000, -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 0 3px 0 #000, 3px 0 0 #000, 0 -3px 0 #000, -3px 0 0 #000, 0 4px 8px rgba(0,0,0,0.8)",
            }}
          >
            {grp.title}
          </div>

          {/* Items: Clean typography without dark pill containers */}
          <div className="flex flex-col gap-0.5">
            {grp.ids.map((id) => {
              const item = items.find((it) => it.id === id);
              const slot = timingSlots.find((s) => s.question_id === id);
              const isRevealed = slot && frame >= slot.reveal_frame;
              const isActive = slot && frame >= slot.start_frame && frame <= slot.end_frame;

              let label = `${id}.`;
              if (isRevealed) {
                if (id === 10) {
                  label = `${id}. Пиши в коммы`;
                } else if (item?.answer_text) {
                  label = `${id}. ${item.answer_text}`;
                }
              }

              return (
                <div
                  key={id}
                  className="text-[38px] font-black tracking-tight transition-transform duration-150"
                  style={{
                    color: grp.color,
                    WebkitTextStroke: "2.5px #000000",
                    textShadow:
                      "3px 3px 0 #000, -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 0 3px 0 #000, 3px 0 0 #000, 0 -3px 0 #000, -3px 0 0 #000, 0 4px 6px rgba(0,0,0,0.8)",
                    transform: isActive ? "scale(1.05)" : "scale(1)",
                    transformOrigin: "left center",
                  }}
                >
                  {label}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};

import React from "react";
import { useCurrentFrame } from "remotion";
import { VisualQuizItem, VisualQuizTimingSlot } from "../types";

interface ProgressiveLadderProps {
  items: VisualQuizItem[];
  timingSlots: VisualQuizTimingSlot[];
  hookEndFrame: number;
  language?: string;
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
  language = "ru",
}) => {
  const frame = useCurrentFrame();

  if (frame < hookEndFrame) {
    return null;
  }

  const isEn = language.toLowerCase().startsWith("en");

  // Groups matching reference video
  const groups = [
    { title: isEn ? "Easy" : "Лёгкий", color: TIER_COLORS.easy, ids: [1, 2, 3] },
    { title: isEn ? "Medium" : "Средний", color: TIER_COLORS.medium, ids: [4, 5, 6] },
    { title: isEn ? "Hard" : "Сложный", color: TIER_COLORS.hard, ids: [7, 8, 9] },
    { title: isEn ? "Master" : "Мастер", color: TIER_COLORS.master, ids: [10] },
  ];

  return (
    <div
      style={{
        position: "absolute",
        left: 125,
        top: 200,
        width: 400,
        display: "flex",
        flexDirection: "column",
        gap: 18,
        fontFamily: "'Rubik', sans-serif",
      }}
      className="z-20 pointer-events-none select-none"
    >
      {groups.map((grp, gIdx) => (
        <div key={gIdx} className="flex flex-col gap-0.5">
          {/* Category Header */}
          <div
            className="text-[45px] font-black tracking-tight"
            style={{
              color: grp.color,
              fontFamily: "'Rubik', sans-serif",
              paintOrder: "stroke fill",
              WebkitTextStroke: "3px #000000",
              textShadow: "0 3px 6px rgba(0,0,0,0.7)",
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
                  label = isEn ? `${id}. Write in comments` : `${id}. Пиши в коммы`;
                } else if (item?.answer_text) {
                  label = `${id}. ${item.answer_text}`;
                }
              }

              return (
                <div
                  key={id}
                  className="text-[40px] font-black tracking-tight transition-transform duration-150"
                  style={{
                    color: grp.color,
                    fontFamily: "'Rubik', sans-serif",
                    paintOrder: "stroke fill",
                    WebkitTextStroke: "2.5px #000000",
                    textShadow: "0 3px 6px rgba(0,0,0,0.6)",
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

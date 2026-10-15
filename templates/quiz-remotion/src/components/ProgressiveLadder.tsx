import React from "react";
import { useCurrentFrame } from "remotion";
import { VisualQuizItem, VisualQuizTimingSlot } from "../types";

interface ProgressiveLadderProps {
  items: VisualQuizItem[];
  timingSlots: VisualQuizTimingSlot[];
  hookEndFrame: number;
}

const TIER_COLORS = {
  easy: "#22C55E",
  medium: "#FACC15",
  hard: "#EF4444",
  master: "#EC4899",
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

  // Groups
  const groups = [
    { title: "Легкий уровень", color: TIER_COLORS.easy, ids: [1, 2, 3] },
    { title: "Средний уровень", color: TIER_COLORS.medium, ids: [4, 5, 6] },
    { title: "Эксперт", color: TIER_COLORS.hard, ids: [7, 8, 9] },
    { title: "Мастер", color: TIER_COLORS.master, ids: [10] },
  ];

  return (
    <div
      style={{
        position: "absolute",
        left: 80,
        top: 380,
        width: 460,
        height: 870,
      }}
      className="flex flex-col justify-between py-2 z-20"
    >
      {groups.map((grp, gIdx) => (
        <div key={gIdx} className="space-y-1.5">
          <div
            className="text-[20px] font-black uppercase tracking-wider flex items-center gap-2 drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)]"
            style={{ color: grp.color }}
          >
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: grp.color, boxShadow: `0 0 10px ${grp.color}` }}
            />
            {grp.title}
          </div>

          <div className="space-y-1">
            {grp.ids.map((id) => {
              const item = items.find((it) => it.id === id);
              const slot = timingSlots.find((s) => s.question_id === id);
              const isRevealed = slot && frame >= slot.reveal_frame;
              const isActive = slot && frame >= slot.start_frame && frame <= slot.end_frame;

              let text = "";
              if (id === 10) {
                text = isRevealed ? "Пиши в коммы" : "???";
              } else {
                text = isRevealed ? item?.answer_text || "" : "???";
              }

              return (
                <div
                  key={id}
                  className={`flex items-center gap-3 px-3 py-1.5 rounded-xl border transition-all duration-200 ${
                    isActive
                      ? "bg-white/20 border-white/40 shadow-lg scale-[1.02]"
                      : "bg-slate-900/60 border-white/10"
                  }`}
                >
                  <span
                    className="font-black text-lg w-7 h-7 flex items-center justify-center rounded-lg"
                    style={{
                      backgroundColor: `${grp.color}22`,
                      color: grp.color,
                      border: `1px solid ${grp.color}44`,
                    }}
                  >
                    {id}
                  </span>
                  <span
                    className={`font-black text-xl tracking-wide truncate ${
                      isRevealed ? "text-white" : "text-slate-500"
                    }`}
                    style={{
                      textShadow:
                        "2px 2px 0 #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 0 2px 0 #000, 2px 0 0 #000, 0 -2px 0 #000, -2px 0 0 #000",
                    }}
                  >
                    {text}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};

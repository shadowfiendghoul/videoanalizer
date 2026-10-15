import React from "react";
import { spring, useVideoConfig } from "remotion";
import { AudioCueSheet, QuizChallenge, QuizItem } from "../types";

interface QuestionLadderProps {
  challenge: QuizChallenge;
  cueSheet: AudioCueSheet;
  currentFrame: number;
}

export const QuestionLadder: React.FC<QuestionLadderProps> = ({
  challenge,
  cueSheet,
  currentFrame,
}) => {
  const { fps } = useVideoConfig();

  // Flatten all questions 1-9 in order
  const allQuestions: QuizItem[] = [];
  challenge.tiers.forEach((tier) => {
    tier.questions.forEach((q) => {
      allQuestions.push(q);
    });
  });
  allQuestions.sort((a, b) => a.question_number - b.question_number);

  // Map cue by question number
  const cueMap = new Map<number, (typeof cueSheet.cues)[0]>();
  cueSheet.cues.forEach((cue) => {
    cueMap.set(cue.question_number, cue);
  });

  const isRu = challenge.language !== "en";

  const tierSections = [
    {
      title: isRu ? "Легкий уровень" : "Easy Level",
      color: "#22C55E",
      questions: allQuestions.filter((q) => q.question_number <= 3),
    },
    {
      title: isRu ? "Средний уровень" : "Medium Level",
      color: "#FACC15",
      questions: allQuestions.filter(
        (q) => q.question_number >= 4 && q.question_number <= 6
      ),
    },
    {
      title: isRu ? "Эксперт" : "Expert",
      color: "#EF4444",
      questions: allQuestions.filter((q) => q.question_number >= 7),
    },
  ];

  return (
    <div className="absolute left-[105px] top-[50%] -translate-y-1/2 flex flex-col gap-4 z-20">
      {tierSections.map((section) => (
        <div key={section.title} className="flex flex-col gap-2">
          {/* Level Tier Header */}
          <div
            className="flex items-center gap-2.5 font-black tracking-wide text-2xl select-none"
            style={{
              color: section.color,
              filter: "drop-shadow(0px 2px 4px rgba(0, 0, 0, 0.95))",
            }}
          >
            <span
              className="w-2.5 h-2.5 rounded-full inline-block flex-shrink-0"
              style={{
                backgroundColor: section.color,
                boxShadow: `0 0 10px ${section.color}`,
              }}
            />
            <span>{section.title}</span>
          </div>

          {/* Question Rows */}
          <div className="flex flex-col gap-2">
            {section.questions.map((q) => {
              const num = q.question_number;
              const cue = cueMap.get(num);
              const isRevealed = cue ? currentFrame >= cue.reveal_frame : false;
              const isFinal = num === 9;

              let popScale = 1;
              if (isRevealed && cue) {
                popScale = spring({
                  frame: currentFrame - cue.reveal_frame,
                  fps,
                  config: {
                    damping: 14,
                    mass: 0.7,
                    stiffness: 100,
                  },
                });
              }

              return (
                <div
                  key={num}
                  className="flex items-center font-black tracking-wide"
                  style={{
                    filter: "drop-shadow(0px 3px 6px rgba(0, 0, 0, 0.9))",
                    fontSize: "clamp(26px, 3.2vw, 42px)",
                  }}
                >
                  {isFinal ? (
                    <span className="inline-flex items-center justify-center w-14 h-14 rounded-full border-2 border-white bg-red-600 text-white text-3xl font-black mr-3.5 shadow-xl flex-shrink-0">
                      9
                    </span>
                  ) : (
                    <span
                      style={{ color: section.color }}
                      className="font-black mr-3.5 w-14 text-left flex-shrink-0 text-4xl leading-none"
                    >
                      {num}.
                    </span>
                  )}

                  {isRevealed && (
                    <span
                      style={{
                        transform: `scale(${popScale})`,
                        transformOrigin: "left center",
                        fontSize: "clamp(24px, 3vw, 38px)",
                        maxWidth: "380px",
                        lineHeight: 1.15,
                      }}
                      className="text-white font-black tracking-wide uppercase drop-shadow-[0_2px_6px_rgba(0,0,0,0.9)] truncate"
                    >
                      {q.correct_answer}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};

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

  return (
    <div className="absolute left-16 top-[38%] -translate-y-1/2 flex flex-col gap-5 z-20">
      {allQuestions.map((q) => {
        const num = q.question_number;
        const cue = cueMap.get(num);
        const isRevealed = cue ? currentFrame >= cue.reveal_frame : false;

        // Colors matching @dreaaam33: 1-4 Green, 5-8 Yellow, 9 Red
        const isGreen = num <= 4;
        const isYellow = num >= 5 && num <= 8;
        const isRed = num === 9;

        const numberColor = isGreen
          ? "#22C55E"
          : isYellow
          ? "#FACC15"
          : "#EF4444";

        let popScale = 1;
        if (isRevealed && cue) {
          popScale = spring({
            frame: currentFrame - cue.reveal_frame,
            fps,
            config: {
              damping: 12,
              mass: 0.5,
              stiffness: 140,
            },
          });
        }

        return (
          <div
            key={num}
            className="flex items-center font-black tracking-wide"
            style={{
              filter: "drop-shadow(0px 3px 6px rgba(0, 0, 0, 0.9))",
              fontSize: "clamp(26px, 3.2vw, 44px)",
            }}
          >
            {isRed ? (
              <span className="inline-flex items-center justify-center w-12 h-12 rounded-full border-2 border-white bg-red-600 text-white text-3xl font-black mr-3 shadow-lg flex-shrink-0">
                9
              </span>
            ) : (
              <span
                style={{ color: numberColor }}
                className="font-black mr-3 w-10 text-left flex-shrink-0"
              >
                {num}.
              </span>
            )}

            {isRevealed && (
              <span
                style={{
                  transform: `scale(${popScale})`,
                  transformOrigin: "left center",
                  fontSize: "clamp(26px, 3.2vw, 44px)",
                  maxWidth: "760px",
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
  );
};

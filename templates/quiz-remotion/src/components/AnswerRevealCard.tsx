import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { WordCue } from "../types";

interface AnswerRevealCardProps {
  correctAnswer: string;
  funFact: string;
  answerWords: WordCue[];
  themeColor: string;
}

export const AnswerRevealCard: React.FC<AnswerRevealCardProps> = ({
  correctAnswer,
  funFact,
  answerWords,
  themeColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({
    frame,
    fps,
    config: {
      damping: 11,
      mass: 0.5,
      stiffness: 130,
    },
  });

  const currentMs = (frame / fps) * 1000;

  return (
    <div
      className="absolute top-[800px] left-0 right-0 flex flex-col items-center justify-center px-8 z-30"
      style={{
        transform: `scale(${scale})`,
        transformOrigin: "center center",
      }}
    >
      <div
        className="w-full max-w-[960px] p-8 rounded-3xl backdrop-blur-2xl flex flex-col items-center justify-center text-center shadow-2xl relative overflow-hidden"
        style={{
          background: "linear-gradient(145deg, rgba(15, 23, 42, 0.94) 0%, rgba(9, 14, 26, 0.96) 100%)",
          boxShadow: "0 30px 70px rgba(0, 0, 0, 0.85), 0 0 45px rgba(34, 197, 94, 0.35)",
        }}
      >
        {/* Ambient Green Glow Orb */}
        <div className="absolute -top-16 -right-16 w-56 h-56 rounded-full bg-emerald-500/25 blur-3xl pointer-events-none" />

        {/* Badge Header */}
        <div className="flex items-center gap-2 px-6 py-2 rounded-full bg-emerald-500 text-slate-950 font-black text-sm uppercase tracking-widest shadow-lg mb-4">
          <span>✓</span>
          <span>CORRECT ANSWER</span>
        </div>

        {/* Revealed Answer Text */}
        <h1
          className="text-6xl font-black text-white tracking-wide uppercase drop-shadow-2xl mb-6 text-center leading-tight"
          style={{
            textShadow: "0 0 25px rgba(34, 197, 94, 0.8), 0 0 50px rgba(34, 197, 94, 0.5)",
          }}
        >
          {correctAnswer}
        </h1>

        {/* Fun Fact Section */}
        {funFact && (
          <div className="w-full p-4 rounded-2xl bg-white/5 text-slate-200 text-lg font-medium leading-relaxed mb-4 text-center">
            💡 <span className="font-semibold text-emerald-400">Fact:</span> {funFact}
          </div>
        )}

        {/* Answer Voiceover Karaoke Captions */}
        {answerWords && answerWords.length > 0 && (
          <div className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 mt-2">
            {answerWords.map((item, index) => {
              const isSpoken = currentMs >= item.start_ms;
              const isActive = currentMs >= item.start_ms && currentMs <= item.end_ms;

              let style: React.CSSProperties = {
                color: "rgba(255, 255, 255, 0.5)",
              };

              if (isActive) {
                style = {
                  color: "#22C55E",
                  transform: "scale(1.15)",
                  textShadow: "0 0 15px #22C55E",
                  fontWeight: 900,
                };
              } else if (isSpoken) {
                style = {
                  color: "#FFFFFF",
                  fontWeight: 700,
                };
              }

              return (
                <span
                  key={`${item.word}-${index}`}
                  className="text-2xl font-bold uppercase inline-block mx-0.5 transition-all duration-75"
                  style={style}
                >
                  {item.word}
                </span>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

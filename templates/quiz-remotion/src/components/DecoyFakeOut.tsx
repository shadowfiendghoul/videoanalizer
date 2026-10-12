import React from "react";
import { spring, useVideoConfig } from "remotion";

export interface DecoyFakeOutProps {
  currentFrame: number;
  revealFrame: number;
  questionNumber: number;
  correctAnswer: string;
  decoyAnswer?: string | null;
  enabled?: boolean;
}

export const DecoyFakeOut: React.FC<DecoyFakeOutProps> = ({
  currentFrame,
  revealFrame,
  questionNumber,
  correctAnswer,
  decoyAnswer,
  enabled = true,
}) => {
  const { fps } = useVideoConfig();

  // Decoy tease applies specifically to Question 4 and Question 7
  if (!enabled || (questionNumber !== 4 && questionNumber !== 7)) {
    return null;
  }

  // 0.35s tease window before reveal
  const teaseDurationFrames = Math.round(fps * 0.35);
  const startFrame = revealFrame - teaseDurationFrames;
  // Hold the confirmation stamp for 1.8s so the viewer can read it clearly!
  const endFrame = revealFrame + Math.round(fps * 1.8);

  if (currentFrame < startFrame || currentFrame > endFrame) {
    return null;
  }

  const isRevealed = currentFrame >= revealFrame;
  const fallbackDecoy = questionNumber === 4 ? "ПАРИЖ" : "СОЛНЦЕ";
  const decoyText = decoyAnswer || fallbackDecoy;

  // Smooth cinematic spring animation for stamp punch
  const animFrame = isRevealed ? currentFrame - revealFrame : currentFrame - startFrame;
  const scale = spring({
    frame: animFrame,
    fps,
    config: {
      damping: 15,
      mass: 0.7,
      stiffness: 100,
    },
  });

  return (
    <div className="absolute top-[48%] left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 pointer-events-none">
      {!isRevealed ? (
        // Fake Decoy Stamp (0.3s tease)
        <div
          style={{
            transform: `scale(${scale}) rotate(-6deg)`,
            boxShadow: "0 0 40px rgba(239, 68, 68, 0.7), 0 20px 40px rgba(0,0,0,0.8)",
          }}
          className="flex items-center space-x-3 px-8 py-4 rounded-3xl bg-red-950/95 border-4 border-red-500 backdrop-blur-xl animate-pulse"
        >
          <span className="text-4xl">❌</span>
          <span className="text-3xl md:text-4xl font-black text-red-100 tracking-wider uppercase font-mono drop-shadow-md">
            НЕ {decoyText.toUpperCase()}
          </span>
        </div>
      ) : (
        // True Answer Stamp confirmation
        <div
          style={{
            transform: `scale(${scale}) rotate(0deg)`,
            boxShadow: "0 0 50px rgba(34, 197, 94, 0.7), 0 20px 40px rgba(0,0,0,0.8)",
          }}
          className="flex items-center space-x-3 px-8 py-4 rounded-3xl bg-emerald-950/95 border-4 border-emerald-400 backdrop-blur-xl"
        >
          <span className="text-4xl">✅</span>
          <span className="text-3xl md:text-4xl font-black text-emerald-100 tracking-wider uppercase font-mono drop-shadow-md">
            {correctAnswer.toUpperCase()}
          </span>
        </div>
      )}
    </div>
  );
};

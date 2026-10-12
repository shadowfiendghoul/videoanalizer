import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import { CommentTrapConfig } from "../types";

interface CommentTrapOutroProps {
  currentFrame: number;
  totalFrames: number;
  config?: CommentTrapConfig;
}

export const CommentTrapOutro: React.FC<CommentTrapOutroProps> = ({
  currentFrame,
  totalFrames,
  config,
}) => {
  const { fps } = useVideoConfig();

  if (config && config.enabled === false) {
    return null;
  }

  const durationFrames = config?.duration_frames ?? 90; // 1.5s = 90 frames
  const startFrame = Math.max(0, totalFrames - durationFrames);

  if (currentFrame < startFrame) {
    return null;
  }

  const frameInTrap = currentFrame - startFrame;
  const entrance = spring({
    frame: frameInTrap,
    fps,
    config: {
      damping: 16,
      mass: 0.75,
      stiffness: 95,
    },
  });

  const pulse = interpolate(
    Math.sin(frameInTrap * 0.2),
    [-1, 1],
    [0.98, 1.02]
  );

  const text =
    config?.outro_challenge_text ||
    "Если набрал 8+ — ты соврал. Пиши честный счет в комменты! 👇";

  return (
    <div
      style={{
        transform: `translate(-50%, -50%) scale(${entrance * pulse})`,
        filter: "drop-shadow(0px 10px 30px rgba(0, 0, 0, 0.85))",
      }}
      className="absolute top-1/2 left-1/2 z-50 w-[880px] p-8 rounded-3xl bg-slate-950/90 border-4 border-amber-400 shadow-[0_0_50px_rgba(245,158,11,0.5)] backdrop-blur-xl flex flex-col items-center text-center pointer-events-none"
    >
      <div className="text-5xl mb-4 animate-bounce">
        💬🔥
      </div>
      <h2 className="text-3xl font-black uppercase tracking-tight text-white leading-snug drop-shadow-md">
        {text}
      </h2>
      <div className="mt-6 flex items-center gap-3 px-6 py-2.5 rounded-full bg-amber-400/20 border border-amber-400/50 text-amber-300 font-extrabold text-lg tracking-wider uppercase">
        <span>👇 НАПИШИ СВОЙ РЕЗУЛЬТАТ 👇</span>
      </div>
    </div>
  );
};

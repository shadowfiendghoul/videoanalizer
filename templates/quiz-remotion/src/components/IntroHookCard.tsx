import React from "react";
import { Audio, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { WordCue } from "../types";
import { resolveAssetUrl } from "../utils/assets";
import { KaraokeCaptions } from "./KaraokeCaptions";

interface IntroHookCardProps {
  hookText: string;
  audioFile?: string | null;
  words?: WordCue[];
  durationInFrames: number;
}

export const IntroHookCard: React.FC<IntroHookCardProps> = ({
  hookText,
  audioFile,
  words,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Entrance spring animation
  const entrance = spring({
    frame,
    fps,
    config: {
      damping: 15,
      mass: 0.75,
      stiffness: 95,
    },
  });

  // Exit fade out during the last 8 frames before Question 1 starts
  const exitFrames = Math.max(1, durationInFrames - 8);
  const opacity = interpolate(
    frame,
    [0, 6, exitFrames, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const exitScale = interpolate(
    frame,
    [exitFrames, durationInFrames],
    [1, 0.9],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const currentScale = (frame < exitFrames ? entrance : exitScale) * (1 + Math.sin(frame * 0.12) * 0.02);

  return (
    <div
      style={{ opacity }}
      className="absolute inset-0 z-35 flex flex-col items-center justify-center pointer-events-none px-8"
    >
      {/* Intro voiceover audio */}
      {audioFile && <Audio src={resolveAssetUrl(audioFile)} volume={1.0} />}

      {/* Main Viral Hook Badge & Card */}
      <div
        style={{
          transform: `scale(${currentScale})`,
          transformOrigin: "center center",
          background: "linear-gradient(145deg, rgba(15, 23, 42, 0.94) 0%, rgba(9, 14, 26, 0.96) 100%)",
          boxShadow: "0 35px 80px rgba(0, 0, 0, 0.9), 0 0 50px rgba(245, 158, 11, 0.25)",
        }}
        className="w-full max-w-[940px] rounded-[36px] p-8 backdrop-blur-2xl flex flex-col items-center text-center relative overflow-hidden"
      >
        {/* Glow ambient background sphere */}
        <div className="absolute -top-24 -left-24 w-64 h-64 rounded-full bg-amber-500/25 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 w-64 h-64 rounded-full bg-emerald-500/20 blur-3xl pointer-events-none" />

        {/* Top Challenge Badge */}
        <div className="inline-flex items-center gap-2 px-5 py-2 rounded-2xl bg-gradient-to-r from-amber-500/25 to-amber-600/20 shadow-lg mb-4">
          <span className="text-2xl animate-bounce">👑</span>
          <span className="text-amber-400 font-mono font-black text-sm md:text-base tracking-widest uppercase">
            9 ВОПРОСОВ НА IQ
          </span>
          <span className="text-xl">🧠</span>
        </div>

        {/* Hook text in large punchy typography */}
        <h1
          style={{
            fontSize: "clamp(34px, 4.2vw, 54px)",
            lineHeight: 1.2,
            textShadow: "0 4px 18px rgba(0, 0, 0, 0.9), 0 0 25px rgba(245, 158, 11, 0.4)",
          }}
          className="text-white font-black tracking-wide uppercase drop-shadow-2xl"
        >
          {hookText}
        </h1>

        {/* Pulsing sub-label */}
        <div className="mt-4 flex items-center gap-2 text-emerald-400 font-mono text-sm font-bold tracking-wider uppercase">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping inline-block" />
          <span>Начинаем через секунду...</span>
        </div>
      </div>

      {/* Synchronized Karaoke subtitles for spoken words */}
      {words && words.length > 0 && <KaraokeCaptions words={words} />}
    </div>
  );
};

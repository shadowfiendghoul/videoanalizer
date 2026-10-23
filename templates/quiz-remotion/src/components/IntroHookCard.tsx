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

      {/* Main Viral Hook Badge & Text (no box/frame, direct floating typography) */}
      <div
        style={{
          transform: `scale(${currentScale})`,
          transformOrigin: "center center",
        }}
        className="w-full max-w-[960px] flex flex-col items-center text-center relative pointer-events-none"
      >
        {/* Top Challenge Badge */}
        <div className="inline-flex items-center gap-2 px-6 py-2.5 rounded-full bg-black/60 backdrop-blur-md shadow-2xl mb-6">
          <span className="text-2xl animate-bounce">👑</span>
          <span className="text-amber-400 font-mono font-black text-sm md:text-base tracking-widest uppercase">
            9 ВОПРОСОВ НА IQ
          </span>
          <span className="text-xl">🧠</span>
        </div>

        {/* Hook text in large punchy typography directly over background */}
        <h1
          style={{
            fontSize: "clamp(38px, 4.8vw, 64px)",
            lineHeight: 1.15,
            textShadow: "0 6px 20px rgba(0, 0, 0, 0.95), 0 0 35px rgba(0, 0, 0, 0.9), 0 0 10px rgba(0, 0, 0, 0.9)",
          }}
          className="text-white font-black tracking-wide uppercase drop-shadow-2xl"
        >
          {hookText}
        </h1>

        {/* Pulsing sub-label */}
        <div className="mt-6 flex items-center gap-2.5 px-5 py-2 rounded-full bg-black/50 backdrop-blur-sm text-emerald-400 font-mono text-sm font-bold tracking-wider uppercase shadow-xl">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping inline-block" />
          <span>Начинаем через секунду...</span>
        </div>
      </div>

      {/* Synchronized Karaoke subtitles for spoken words */}
      {words && words.length > 0 && <KaraokeCaptions words={words} />}
    </div>
  );
};

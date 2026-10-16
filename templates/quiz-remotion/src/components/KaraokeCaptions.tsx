import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { WordCue } from "../types";

interface KaraokeCaptionsProps {
  words: WordCue[];
  themeColor?: string;
}

export const KaraokeCaptions: React.FC<KaraokeCaptionsProps> = ({
  words,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (!words || words.length === 0) {
    return null;
  }

  // Convert current relative frame to milliseconds
  const currentMs = (frame / fps) * 1000;

  // Instantaneous audio playback synchronization (0ms delay)
  const syncMs = currentMs;

  const firstStart = words[0].start_ms;
  const lastEnd = words[words.length - 1].end_ms;

  // Only display during spoken range
  if (syncMs < firstStart || syncMs > lastEnd + 150) {
    return null;
  }

  // Find currently active word
  let activeWord = words.find(
    (w) => syncMs >= w.start_ms && syncMs <= w.end_ms + 40
  );

  // If between consecutive words during the phrase, hold the latest word
  if (!activeWord && syncMs >= firstStart && syncMs <= lastEnd) {
    activeWord = [...words].reverse().find((w) => syncMs >= w.start_ms);
  }

  if (!activeWord) {
    return null;
  }

  return (
    <div className="absolute bottom-[500px] left-[120px] right-[120px] flex items-center justify-center z-30 pointer-events-none select-none">
      <span
        className="text-6xl md:text-7xl font-black tracking-wide text-white uppercase text-center"
        style={{
          fontFamily: "'Rubik', sans-serif",
          paintOrder: "stroke fill",
          textShadow: "0 8px 16px rgba(0,0,0,0.8)",
          WebkitTextStroke: "3px #000000",
        }}
      >
        {activeWord.word.trim()}
      </span>
    </div>
  );
};

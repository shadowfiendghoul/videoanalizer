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
    <div className="absolute bottom-32 left-0 right-0 flex items-center justify-center px-12 z-30 pointer-events-none">
      <span
        className="text-5xl md:text-6xl font-black tracking-widest uppercase text-white drop-shadow-[0_4px_12px_rgba(0,0,0,0.95)]"
        style={{
          textShadow:
            "0 4px 10px #000000, 0 2px 4px #000000, 0 0 16px rgba(0,0,0,0.9)",
          WebkitTextStroke: "2px #000000",
        }}
      >
        {activeWord.word.trim()}
      </span>
    </div>
  );
};

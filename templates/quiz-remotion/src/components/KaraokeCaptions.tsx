import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { WordCue } from "../types";

export interface SubtitleCue {
  word: string;
  start_ms?: number;
  end_ms?: number;
  start_frame?: number;
  end_frame?: number;
}

interface KaraokeCaptionsProps {
  words: (SubtitleCue | WordCue)[];
  themeColor?: string;
  bottomOffset?: number;
}

export const KaraokeCaptions: React.FC<KaraokeCaptionsProps> = ({
  words,
  bottomOffset = 380,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const sortedWords = React.useMemo(() => {
    if (!words || words.length === 0) return [];
    const list = words.map((w: any) => {
      const s =
        typeof w.start_ms === "number"
          ? w.start_ms
          : ((w.start_frame ?? 0) / fps) * 1000;
      const e =
        typeof w.end_ms === "number"
          ? w.end_ms
          : ((w.end_frame ?? 0) / fps) * 1000;
      return {
        word: (w.word || "").trim(),
        start_ms: s,
        end_ms: e,
      };
    });
    return list.sort((a, b) => a.start_ms - b.start_ms);
  }, [words, fps]);

  if (sortedWords.length === 0) {
    return null;
  }

  // Acoustic alignment from Whisper timestamps with 25ms perceptual display lead (1.5 frames at 60fps)
  const SUBTITLE_LEAD_MS = 25;
  const syncMs = (frame / fps) * 1000 + SUBTITLE_LEAD_MS;

  // Find active word: latest word whose start_ms <= syncMs
  let activeIndex = -1;
  for (let i = 0; i < sortedWords.length; i++) {
    if (syncMs >= sortedWords[i].start_ms) {
      activeIndex = i;
    } else {
      break;
    }
  }

  if (activeIndex === -1) {
    return null;
  }

  const activeWord = sortedWords[activeIndex];
  const nextWord = sortedWords[activeIndex + 1];

  // Duration the active word should be held on screen:
  // If next word follows immediately (gap <= 300ms), hold until next word starts.
  // If there is silence/countdown pause (gap > 300ms), hold for word duration + 120ms then clear.
  const wordDuration = Math.max(200, activeWord.end_ms - activeWord.start_ms);
  const holdUntil = activeWord.start_ms + wordDuration + 120;

  if (nextWord) {
    const gap = nextWord.start_ms - activeWord.end_ms;
    if (gap > 300 && syncMs > holdUntil) {
      return null;
    }
  } else {
    if (syncMs > holdUntil) {
      return null;
    }
  }

  if (!activeWord || !activeWord.word) {
    return null;
  }

  return (
    <div
      style={{ bottom: bottomOffset }}
      className="absolute left-[60px] right-[60px] flex items-center justify-center z-30 pointer-events-none select-none"
    >
      <div
        className="px-8 py-2.5 rounded-2xl flex items-center justify-center"
        style={{
          backgroundColor: "rgba(0, 0, 0, 0.45)",
          backdropFilter: "blur(6px)",
          border: "2px solid rgba(255, 255, 255, 0.15)",
          boxShadow: "0 14px 32px rgba(0, 0, 0, 0.7)",
        }}
      >
        <span
          className="text-6xl md:text-7xl font-black tracking-wide uppercase text-center"
          style={{
            color: "#FFE600",
            fontFamily: "'Rubik', sans-serif",
            paintOrder: "stroke fill",
            textShadow: "0 8px 18px rgba(0,0,0,0.95), 0 0 25px rgba(255,230,0,0.45)",
            WebkitTextStroke: "3.5px #000000",
          }}
        >
          {activeWord.word}
        </span>
      </div>
    </div>
  );
};

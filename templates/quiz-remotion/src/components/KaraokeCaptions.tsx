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
  bottomOffset = 460,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const normalizedWords = React.useMemo(() => {
    if (!words || words.length === 0) return [];
    return words.map((w: any) => {
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
  }, [words, fps]);

  if (normalizedWords.length === 0) {
    return null;
  }

  // Convert current frame to milliseconds
  const syncMs = (frame / fps) * 1000;

  // Find currently active word (active word window + 120ms leeway)
  const activeWord = normalizedWords.find(
    (w) => syncMs >= w.start_ms && syncMs <= w.end_ms + 120
  );

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

import React from "react";
import { Img, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { resolveAssetUrl } from "../utils/assets";

interface QuestionCardProps {
  questionText: string;
  localImagePath: string | null;
  themeColor: string;
}

export const QuestionCard: React.FC<QuestionCardProps> = ({
  questionText,
  localImagePath,
  themeColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({
    frame,
    fps,
    config: {
      damping: 15,
      mass: 0.7,
      stiffness: 110,
    },
  });

  const resolvedImage = localImagePath ? resolveAssetUrl(localImagePath) : null;
  const isVisual = Boolean(resolvedImage);

  // Dynamic text size based on length
  const textLength = questionText.length;
  let textSizeClass = "text-5xl leading-tight";
  if (textLength > 100) {
    textSizeClass = "text-3xl leading-snug";
  } else if (textLength > 60) {
    textSizeClass = "text-4xl leading-snug";
  }

  return (
    <div
      className="absolute top-[260px] left-0 right-0 flex flex-col items-center justify-center px-8 z-10"
      style={{
        transform: `scale(${scale})`,
        transformOrigin: "center center",
      }}
    >
      <div
        className="w-full max-w-[960px] min-h-[380px] p-8 rounded-3xl backdrop-blur-2xl border flex flex-col items-center justify-center text-center shadow-2xl relative overflow-hidden"
        style={{
          background: "rgba(15, 23, 42, 0.82)",
          borderColor: "rgba(255, 255, 255, 0.15)",
          boxShadow: `0 20px 50px rgba(0, 0, 0, 0.6), 0 0 30px ${themeColor}22`,
        }}
      >
        {/* Subtle decorative glow orb behind */}
        <div
          className="absolute -top-20 -left-20 w-48 h-48 rounded-full blur-3xl opacity-30 pointer-events-none"
          style={{ backgroundColor: themeColor }}
        />

        {isVisual ? (
          <div className="flex flex-col items-center justify-center w-full gap-6">
            {/* Visual Asset Container (Flags / Logos / Landmarks) */}
            <div className="w-[600px] h-[320px] rounded-2xl bg-black/40 border border-white/10 flex items-center justify-center p-3 overflow-hidden shadow-inner">
              <Img
                src={resolvedImage!}
                className="max-w-full max-h-full object-contain drop-shadow-xl"
              />
            </div>
            {/* Prompt text below image */}
            <h2
              className="font-black text-white text-center drop-shadow-lg"
              style={{
                fontSize: "clamp(26px, 3.2vw, 44px)",
                lineHeight: 1.25,
                maxWidth: "840px",
                overflowWrap: "break-word",
              }}
            >
              {questionText}
            </h2>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center w-full py-4">
            <h2
              className="font-black text-white text-center tracking-wide drop-shadow-lg"
              style={{
                fontSize: "clamp(26px, 3.2vw, 44px)",
                lineHeight: 1.25,
                maxWidth: "840px",
                overflowWrap: "break-word",
              }}
            >
              {questionText}
            </h2>
          </div>
        )}
      </div>
    </div>
  );
};

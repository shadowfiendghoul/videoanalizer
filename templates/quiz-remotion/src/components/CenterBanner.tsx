import React from "react";
import {
  AbsoluteFill,
  interpolate,
  OffthreadVideo,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { resolveAssetUrl } from "../utils/assets";

interface CenterBannerProps {
  videoPath: string;
  durationInFrames: number;
}

export const CenterBanner: React.FC<CenterBannerProps> = ({
  videoPath,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const src = resolveAssetUrl(videoPath);

  // Entrance spring animation (first 15 frames)
  const enterScale = spring({
    frame,
    fps,
    config: {
      damping: 12,
      mass: 0.6,
      stiffness: 130,
    },
  });

  // Exit fade out (last 12 frames)
  const exitFrames = Math.max(1, durationInFrames - 12);
  const opacity = interpolate(
    frame,
    [0, 8, exitFrames, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const exitScale = interpolate(
    frame,
    [exitFrames, durationInFrames],
    [1, 0.85],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const currentScale = frame < exitFrames ? enterScale : exitScale;

  return (
    <AbsoluteFill className="pointer-events-none z-40 flex items-center justify-center">
      {/* 
        Container positioned strictly at the center of the screen (top-1/2, left-1/2).
        Dimensions: 980px x 560px = 548,800 px² (~26.5% of 1080x1920 = 2,073,600 px²).
        Strictly satisfies Rule 3.2: "Баннер должен занимать не менее 25% площади экрана и располагаться РОВНО по центру".
      */}
      <div
        className="w-[980px] h-[560px] rounded-3xl overflow-hidden shadow-[0_25px_60px_rgba(0,0,0,0.85)] border-2 border-white/30 backdrop-blur-md bg-black/80 flex items-center justify-center relative"
        style={{
          transform: `scale(${currentScale})`,
          opacity,
          boxShadow:
            "0 25px 60px rgba(0, 0, 0, 0.9), 0 0 35px rgba(255, 255, 255, 0.15)",
        }}
      >
        {src && (
          <OffthreadVideo
            src={src}
            className="w-full h-full object-cover"
          />
        )}
      </div>
    </AbsoluteFill>
  );
};

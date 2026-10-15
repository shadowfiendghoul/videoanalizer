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
  videoWidth?: number | null;
  videoHeight?: number | null;
}

export const CenterBanner: React.FC<CenterBannerProps> = ({
  videoPath,
  durationInFrames,
  videoWidth,
  videoHeight,
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

  // Safe bounds on 1080x1920 canvas:
  // maxWidth: 1000px (leaves 40px safe margins on left and right)
  // maxHeight: 720px (leaves comfortable margins for status rank bar and ladder)
  const maxWidth = 1000;
  const maxHeight = 720;

  const aspectRatio =
    videoWidth && videoHeight && videoWidth > 0 && videoHeight > 0
      ? videoWidth / videoHeight
      : 16 / 9;

  let bannerWidth = maxWidth;
  let bannerHeight = bannerWidth / aspectRatio;

  if (bannerHeight > maxHeight) {
    bannerHeight = maxHeight;
    bannerWidth = bannerHeight * aspectRatio;
  }

  bannerWidth = Math.round(bannerWidth);
  bannerHeight = Math.round(bannerHeight);

  const isTransparent = Boolean(src && /\.webm|\.mov/i.test(src));

  return (
    <AbsoluteFill className="pointer-events-none z-40 flex items-center justify-center">
      {/* 
        Container dynamically sized to match banner aspect ratio perfectly.
        Uses object-contain so NO banner is ever cropped.
      */}
      <div
        className={
          isTransparent
            ? "flex items-center justify-center relative drop-shadow-[0_25px_45px_rgba(0,0,0,0.85)]"
            : "rounded-3xl overflow-hidden flex items-center justify-center relative border border-white/20 shadow-[0_25px_60px_rgba(0,0,0,0.85)] bg-black/60"
        }
        style={{
          width: bannerWidth,
          height: bannerHeight,
          transform: `scale(${currentScale})`,
          opacity,
          boxShadow: isTransparent
            ? undefined
            : "0 25px 60px rgba(0, 0, 0, 0.9), 0 0 35px rgba(255, 255, 255, 0.12)",
        }}
      >
        {src && (
          <OffthreadVideo
            src={src}
            className="w-full h-full object-contain"
            transparent={isTransparent}
          />
        )}
      </div>
    </AbsoluteFill>
  );
};

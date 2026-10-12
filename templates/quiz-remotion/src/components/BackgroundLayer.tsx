import React from "react";
import { AbsoluteFill, Freeze, Loop, OffthreadVideo, Sequence, useVideoConfig } from "remotion";
import { resolveAssetUrl } from "../utils/assets";

interface BackgroundLayerProps {
  videoPath: string;
  loopDurationInFrames?: number;
  bannerStartFrame?: number | null;
  bannerDurationFrames?: number | null;
}

export const BackgroundLayer: React.FC<BackgroundLayerProps> = ({
  videoPath,
  loopDurationInFrames,
  bannerStartFrame,
  bannerDurationFrames,
}) => {
  const { durationInFrames } = useVideoConfig();
  const src = resolveAssetUrl(videoPath);

  // Default to entire video duration so the background video plays continuously
  // without jumping/cutting back to 0 every 7.5 seconds (450 frames).
  const effectiveLoopDuration = loopDurationInFrames || durationInFrames;

  const hasBannerPause =
    typeof bannerStartFrame === "number" &&
    typeof bannerDurationFrames === "number" &&
    bannerDurationFrames > 0;

  return (
    <AbsoluteFill className="bg-slate-950">
      {/* Background Video with pause support during promo banner */}
      {src && !hasBannerPause && (
        <Loop durationInFrames={effectiveLoopDuration}>
          <OffthreadVideo
            src={src}
            muted
            className="w-full h-full object-cover opacity-100"
          />
        </Loop>
      )}

      {src && hasBannerPause && (
        <>
          {/* Phase 1: Before banner (normal continuous playback) */}
          <Sequence from={0} durationInFrames={bannerStartFrame!}>
            <OffthreadVideo
              src={src}
              muted
              className="w-full h-full object-cover opacity-100"
            />
          </Sequence>

          {/* Phase 2: During banner (PAUSED / FROZEN on bannerStartFrame) */}
          <Sequence from={bannerStartFrame!} durationInFrames={bannerDurationFrames!}>
            <Freeze frame={bannerStartFrame!}>
              <OffthreadVideo
                src={src}
                muted
                className="w-full h-full object-cover opacity-100"
              />
            </Freeze>
          </Sequence>

          {/* Phase 3: After banner (resumes playing from bannerStartFrame onwards) */}
          <Sequence from={bannerStartFrame! + bannerDurationFrames!}>
            <OffthreadVideo
              src={src}
              startFrom={bannerStartFrame!}
              muted
              className="w-full h-full object-cover opacity-100"
            />
          </Sequence>
        </>
      )}

      {/* Subtle Ambient Vignette and Soft Gradients for Clean Contrast without Darkening */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle at center, rgba(0, 0, 0, 0.05) 0%, rgba(2, 6, 23, 0.35) 100%)",
        }}
      />
      <AbsoluteFill className="bg-gradient-to-b from-black/30 via-transparent to-black/45 pointer-events-none" />
    </AbsoluteFill>
  );
};


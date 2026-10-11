import React from "react";
import { AbsoluteFill, Freeze, Loop, Sequence, Video } from "remotion";
import { resolveAssetUrl } from "../utils/assets";

interface BackgroundLayerProps {
  videoPath: string;
  loopDurationInFrames?: number;
  bannerStartFrame?: number | null;
  bannerDurationFrames?: number | null;
}

export const BackgroundLayer: React.FC<BackgroundLayerProps> = ({
  videoPath,
  loopDurationInFrames = 450, // Loop every 15s (450 frames) to safely loop short backgrounds
  bannerStartFrame,
  bannerDurationFrames,
}) => {
  const src = resolveAssetUrl(videoPath);

  const hasBannerPause =
    typeof bannerStartFrame === "number" &&
    typeof bannerDurationFrames === "number" &&
    bannerDurationFrames > 0;

  return (
    <AbsoluteFill className="bg-slate-950">
      {/* Background Video with pause support during promo banner */}
      {src && !hasBannerPause && (
        <Loop durationInFrames={loopDurationInFrames}>
          <Video
            src={src}
            muted
            delayRenderTimeoutInMilliseconds={120000}
            delayRenderRetries={3}
            className="w-full h-full object-cover opacity-100"
          />
        </Loop>
      )}

      {src && hasBannerPause && (
        <>
          {/* Phase 1: Before banner (normal playback) */}
          <Sequence from={0} durationInFrames={bannerStartFrame!}>
            <Loop durationInFrames={loopDurationInFrames}>
              <Video
                src={src}
                muted
                delayRenderTimeoutInMilliseconds={120000}
                delayRenderRetries={3}
                className="w-full h-full object-cover opacity-100"
              />
            </Loop>
          </Sequence>

          {/* Phase 2: During banner (PAUSED / FROZEN on bannerStartFrame) */}
          <Sequence from={bannerStartFrame!} durationInFrames={bannerDurationFrames!}>
            <Freeze frame={bannerStartFrame! % loopDurationInFrames}>
              <Video
                src={src}
                muted
                delayRenderTimeoutInMilliseconds={120000}
                delayRenderRetries={3}
                className="w-full h-full object-cover opacity-100"
              />
            </Freeze>
          </Sequence>

          {/* Phase 3: After banner (resumes playing from bannerStartFrame) */}
          <Sequence from={bannerStartFrame! + bannerDurationFrames!}>
            <Loop durationInFrames={loopDurationInFrames}>
              <Video
                src={src}
                startFrom={bannerStartFrame! % loopDurationInFrames}
                muted
                delayRenderTimeoutInMilliseconds={120000}
                delayRenderRetries={3}
                className="w-full h-full object-cover opacity-100"
              />
            </Loop>
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

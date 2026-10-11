import React from "react";
import { AbsoluteFill, Loop, Video } from "remotion";
import { resolveAssetUrl } from "../utils/assets";

interface BackgroundLayerProps {
  videoPath: string;
  loopDurationInFrames?: number;
}

export const BackgroundLayer: React.FC<BackgroundLayerProps> = ({
  videoPath,
  loopDurationInFrames = 450, // Loop every 15s (450 frames) to safely loop short backgrounds
}) => {
  const src = resolveAssetUrl(videoPath);

  return (
    <AbsoluteFill className="bg-slate-950">
      {/* Background Video wrapped in Loop guard */}
      {src && (
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

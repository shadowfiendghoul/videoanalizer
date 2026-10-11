import React from "react";
import { AbsoluteFill, Video } from "remotion";
import { resolveAssetUrl } from "../utils/assets";

interface BackgroundLayerProps {
  videoPath: string;
}

export const BackgroundLayer: React.FC<BackgroundLayerProps> = ({ videoPath }) => {
  const src = resolveAssetUrl(videoPath);

  return (
    <AbsoluteFill className="bg-slate-950">
      {/* Background Video */}
      {src && (
        <Video
          src={src}
          loop
          muted
          delayRenderTimeoutInMilliseconds={120000}
          delayRenderRetries={3}
          className="w-full h-full object-cover opacity-85"
        />
      )}

      {/* Dark Ambient Vignette and Gradients for High Text Contrast */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle at center, rgba(15, 23, 42, 0.45) 0%, rgba(2, 6, 23, 0.85) 100%)",
        }}
      />
      <AbsoluteFill className="bg-gradient-to-b from-black/80 via-transparent to-black/90 pointer-events-none" />
    </AbsoluteFill>
  );
};

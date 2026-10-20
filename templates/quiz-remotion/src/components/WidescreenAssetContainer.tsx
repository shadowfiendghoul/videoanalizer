import React from "react";
import { Img, interpolate, spring, staticFile, useVideoConfig } from "remotion";
import { AssetDisplayMode } from "../types";

interface WidescreenAssetContainerProps {
  assetMode: AssetDisplayMode;
  assetPath?: string | null;
  assetUrl?: string | null;
  promptText: string;
  applyProceduralMask?: boolean;
  isRevealed?: boolean;
  themeColor?: string;
  relativeFrame?: number;
  containerLeft?: number;
  containerTop?: number;
  containerWidth?: number;
  containerHeight?: number;
}

export const WidescreenAssetContainer: React.FC<WidescreenAssetContainerProps> = ({
  assetMode,
  assetPath,
  assetUrl,
  promptText,
  applyProceduralMask = true,
  isRevealed = false,
  themeColor = "#00F0FF",
  relativeFrame = 0,
  containerLeft = 230,
  containerTop = 130,
  containerWidth = 1460,
  containerHeight = 770,
}) => {
  const frame = relativeFrame;
  const { fps } = useVideoConfig();

  const rawSource = assetPath || assetUrl || null;
  const imageSource = rawSource
    ? rawSource.startsWith("http://") || rawSource.startsWith("https://") || rawSource.startsWith("data:")
      ? rawSource
      : staticFile(rawSource)
    : null;

  // 1. Dynamic Spring Entrance (Ease-out bounce)
  const entrance = spring({
    frame,
    fps,
    config: {
      damping: 13,
      mass: 0.65,
      stiffness: 110,
    },
  });
  const containerScale = interpolate(entrance, [0, 1], [0.88, 1]);
  const containerTranslateY = interpolate(entrance, [0, 1], [35, 0]);
  const containerOpacity = interpolate(frame, [0, 6], [0.4, 1], {
    extrapolateRight: "clamp",
  });

  // 2. Cyber Flash Burst on Entrance (frames 0 to 14)
  const flashOpacity = interpolate(frame, [0, 2, 14], [0, 0.85, 0], {
    extrapolateRight: "clamp",
  });

  // Waveform animation for AUDIO_SFX mode
  const pulseScale = 1 + 0.08 * Math.sin(frame * 0.2);
  const glowOpacity = 0.6 + 0.4 * Math.sin(frame * 0.15);

  // Radar sweep angle for MINIMAP mode
  const sweepAngle = (frame * 3) % 360;

  // Silhouette transition: when revealed, transition from brightness(0) to brightness(1)
  const silhouetteBrightness = isRevealed
    ? interpolate(frame, [360, 390], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;

  return (
    <div
      style={{
        position: "absolute",
        left: containerLeft,
        top: containerTop,
        width: containerWidth,
        height: containerHeight,
        borderRadius: 36,
        background: "#080B11",
        border: "8px solid #FFFFFF",
        boxShadow: "0 24px 60px rgba(0, 0, 0, 0.8), 0 4px 16px rgba(0, 0, 0, 0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
        zIndex: 5,
        transform: `translateY(${containerTranslateY}px) scale(${containerScale})`,
        opacity: containerOpacity,
      }}
    >
      {/* Dynamic Cyber Flash Overlay */}
      {flashOpacity > 0.01 && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            background: `radial-gradient(ellipse at center, rgba(0, 240, 255, ${flashOpacity}) 0%, rgba(255, 255, 255, ${flashOpacity * 0.6}) 25%, transparent 70%)`,
            boxShadow: `inset 0 0 60px rgba(0, 240, 255, ${flashOpacity})`,
            mixBlendMode: "screen",
            zIndex: 25,
          }}
        />
      )}

      {/* 1. AUDIO_SFX Mode */}
      {assetMode === "audio_sfx" && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            width: "100%",
            height: "100%",
          }}
        >
          {/* Animated Glowing Waveform / Sound Icon */}
          <div
            style={{
              position: "relative",
              width: 200,
              height: 200,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transform: `scale(${pulseScale})`,
            }}
          >
            {/* Outer Glowing Rings */}
            <div
              style={{
                position: "absolute",
                width: 180,
                height: 180,
                borderRadius: "50%",
                border: `2px solid ${themeColor}`,
                opacity: glowOpacity * 0.45,
                boxShadow: `0 0 35px ${themeColor}`,
              }}
            />
            <div
              style={{
                position: "absolute",
                width: 140,
                height: 140,
                borderRadius: "50%",
                border: `2px dashed ${themeColor}`,
                opacity: glowOpacity * 0.75,
              }}
            />

            {/* Audio Wave Bars */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                height: 80,
              }}
            >
              {[0.4, 0.7, 1.0, 0.85, 0.6, 0.9, 0.5, 0.3].map((baseHeight, i) => {
                const waveH =
                  20 +
                  60 *
                    baseHeight *
                    Math.abs(Math.sin((frame + i * 15) * 0.15));
                return (
                  <div
                    key={`wave_${i}`}
                    style={{
                      width: 8,
                      height: waveH,
                      borderRadius: 4,
                      backgroundColor: themeColor,
                      boxShadow: `0 0 16px ${themeColor}`,
                    }}
                  />
                );
              })}
            </div>
          </div>

          <div
            style={{
              fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
              fontSize: 24,
              fontWeight: 900,
              letterSpacing: "0.1em",
              color: "#FFFFFF",
              textTransform: "uppercase",
              marginTop: 24,
              textShadow: `0 0 16px ${themeColor}99, 0 2px 4px rgba(0, 0, 0, 0.9)`,
            }}
          >
            LISTEN CAREFULLY...
          </div>
        </div>
      )}

      {/* 2. MINIMAP Mode (Circular SVG Radar HUD) */}
      {assetMode === "minimap" && imageSource && (
        <div
          style={{
            position: "relative",
            width: 480,
            height: 480,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Img
            src={imageSource}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              clipPath: applyProceduralMask ? "circle(50% at 50% 50%)" : "none",
            }}
          />

          {/* Tactical SVG Radar Grid & Sweep Overlay */}
          {applyProceduralMask && (
            <svg
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: "100%",
                pointerEvents: "none",
              }}
              viewBox="0 0 480 480"
            >
              {/* Radar Rings */}
              <circle cx="240" cy="240" r="80" fill="none" stroke={themeColor} strokeWidth="1" strokeDasharray="4 4" opacity="0.4" />
              <circle cx="240" cy="240" r="160" fill="none" stroke={themeColor} strokeWidth="1" strokeDasharray="4 4" opacity="0.4" />
              <circle cx="240" cy="240" r="236" fill="none" stroke={themeColor} strokeWidth="2" opacity="0.6" />

              {/* Crosshairs */}
              <line x1="240" y1="0" x2="240" y2="480" stroke={themeColor} strokeWidth="1" opacity="0.3" />
              <line x1="0" y1="240" x2="480" y2="240" stroke={themeColor} strokeWidth="1" opacity="0.3" />

              {/* Rotating Sweep Line */}
              <line
                x1="240"
                y1="240"
                x2={240 + 236 * Math.cos((sweepAngle * Math.PI) / 180)}
                y2={240 + 236 * Math.sin((sweepAngle * Math.PI) / 180)}
                stroke={themeColor}
                strokeWidth="2"
                opacity="0.8"
              />
            </svg>
          )}
        </div>
      )}

      {/* 3. SILHOUETTE Mode */}
      {assetMode === "silhouette" && imageSource && (
        <div
          style={{
            width: "100%",
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 30,
          }}
        >
          <Img
            src={imageSource}
            style={{
              maxWidth: 1140,
              maxHeight: 540,
              objectFit: "contain",
              filter: applyProceduralMask
                ? `brightness(${silhouetteBrightness}) drop-shadow(0 0 20px ${themeColor}88)`
                : "none",
              transition: "filter 0.5s ease-out",
            }}
          />
        </div>
      )}

      {/* 4. SCREENSHOT / GAME_OVER / CUSTOM Mode */}
      {assetMode !== "audio_sfx" && assetMode !== "minimap" && assetMode !== "silhouette" && imageSource && (
        <div
          style={{
            width: "100%",
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
          }}
        >
          <Img
            src={imageSource}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
            }}
          />
        </div>
      )}

      {/* 5. Missing Asset Fallback Placeholder */}
      {assetMode !== "audio_sfx" && !imageSource && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: 40,
            textAlign: "center",
          }}
        >
          <div
            style={{
              width: 88,
              height: 88,
              borderRadius: 20,
              background: "linear-gradient(180deg, #21262D 0%, #161B22 100%)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: 16,
              boxShadow: "0 8px 24px rgba(0, 0, 0, 0.5)",
            }}
          >
            <span style={{ fontSize: 40, color: "#8B949E" }}>🎮</span>
          </div>
          <div
            style={{
              fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
              fontSize: 26,
              fontWeight: 900,
              color: "#FFFFFF",
              marginBottom: 8,
              maxWidth: 800,
              textShadow: "0 2px 6px rgba(0, 0, 0, 0.9)",
            }}
          >
            {promptText || "GUESS THE GAME"}
          </div>
          <div
            style={{
              fontFamily: "'Montserrat', 'Inter Tight', sans-serif",
              fontSize: 16,
              fontWeight: 700,
              color: "#8B949E",
              letterSpacing: "0.08em",
            }}
          >
            MEDIA LOADING...
          </div>
        </div>
      )}
    </div>
  );
};

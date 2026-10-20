import React from "react";
import { Img, interpolate, staticFile, useCurrentFrame } from "remotion";
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
}

export const WidescreenAssetContainer: React.FC<WidescreenAssetContainerProps> = ({
  assetMode,
  assetPath,
  assetUrl,
  promptText,
  applyProceduralMask = true,
  isRevealed = false,
  themeColor = "#00E5FF",
  relativeFrame = 0,
}) => {
  const frame = relativeFrame;
  const rawSource = assetPath || assetUrl || null;
  const imageSource = rawSource
    ? rawSource.startsWith("http://") || rawSource.startsWith("https://") || rawSource.startsWith("data:")
      ? rawSource
      : staticFile(rawSource)
    : null;

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
        left: 360,
        top: 170,
        width: 1200,
        height: 600,
        borderRadius: 20,
        backgroundColor: "#161B22",
        border: "2px solid #21262D",
        boxShadow: "0 12px 36px rgba(0, 0, 0, 0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
        zIndex: 5,
      }}
    >
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
              width: 180,
              height: 180,
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
                width: 160,
                height: 160,
                borderRadius: "50%",
                border: `2px solid ${themeColor}`,
                opacity: glowOpacity * 0.4,
                boxShadow: `0 0 30px ${themeColor}`,
              }}
            />
            <div
              style={{
                position: "absolute",
                width: 120,
                height: 120,
                borderRadius: "50%",
                border: `2px dashed ${themeColor}`,
                opacity: glowOpacity * 0.7,
              }}
            />

            {/* Audio Wave Bars */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                zIndex: 2,
              }}
            >
              {[0.4, 0.7, 1.0, 0.6, 0.9, 0.5, 0.8].map((hFactor, i) => {
                const barH = 24 + 48 * Math.abs(Math.sin((frame * 0.25) + i * 0.8)) * hFactor;
                return (
                  <div
                    key={i}
                    style={{
                      width: 8,
                      height: barH,
                      backgroundColor: themeColor,
                      borderRadius: 4,
                      boxShadow: `0 0 12px ${themeColor}`,
                    }}
                  />
                );
              })}
            </div>
          </div>

          <div
            style={{
              marginTop: 24,
              fontFamily: "system-ui, sans-serif",
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: "0.1em",
              color: "#8B949E",
              textTransform: "uppercase",
            }}
          >
            {promptText || "СЛУШАЙТЕ ЗВУК И УГАДАЙТЕ ПРЕДМЕТ"}
          </div>
        </div>
      )}

      {/* 2. MINIMAP / RADAR Mode */}
      {assetMode === "minimap" && imageSource && (
        <div
          style={{
            position: "relative",
            width: 480,
            height: 480,
            borderRadius: "50%",
            overflow: "hidden",
            boxShadow: `0 0 40px rgba(0, 229, 255, 0.3)`,
            border: `3px solid ${themeColor}`,
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
              borderRadius: 12,
              filter: applyProceduralMask
                ? `brightness(${silhouetteBrightness}) drop-shadow(0 0 20px rgba(0, 229, 255, ${1 - silhouetteBrightness}))`
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
            padding: 30,
          }}
        >
          <Img
            src={imageSource}
            style={{
              maxWidth: 1140,
              maxHeight: 540,
              objectFit: "contain",
              borderRadius: 12,
              boxShadow: "0 8px 24px rgba(0, 0, 0, 0.5)",
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
              width: 80,
              height: 80,
              borderRadius: 16,
              backgroundColor: "#21262D",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: 16,
            }}
          >
            <span style={{ fontSize: 36, color: "#8B949E" }}>🎮</span>
          </div>
          <div
            style={{
              fontFamily: "system-ui, sans-serif",
              fontSize: 26,
              fontWeight: 700,
              color: "#FFFFFF",
              marginBottom: 8,
            }}
          >
            {promptText || "ВОПРОС ВИКТОРИНЫ"}
          </div>
          <div
            style={{
              fontFamily: "system-ui, sans-serif",
              fontSize: 16,
              color: "#8B949E",
            }}
          >
            Медиафайл загружается...
          </div>
        </div>
      )}
    </div>
  );
};

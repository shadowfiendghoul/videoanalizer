import React from "react";
import { useCurrentFrame } from "remotion";

export const WidescreenGamingPattern: React.FC = () => {
  const frame = useCurrentFrame();

  // Subtle shimmer between 10% and 15% opacity
  const shimmer = 0.11 + 0.035 * Math.sin(frame * 0.045);

  // Slow smooth drift (180px repeat period)
  const shiftX = (frame * 0.15) % 180;
  const shiftY = (frame * 0.25) % 180;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        zIndex: 1,
        opacity: shimmer,
        overflow: "hidden",
      }}
    >
      <svg width="1920" height="1080" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern
            id="gamingGeometricPattern"
            width="180"
            height="180"
            patternUnits="userSpaceOnUse"
            patternTransform={`translate(${shiftX}, ${shiftY})`}
          >
            {/* 1. Cross (✕) */}
            <line x1="22" y1="22" x2="42" y2="42" stroke="#FFFFFF" strokeWidth="2.2" strokeLinecap="round" />
            <line x1="42" y1="22" x2="22" y2="42" stroke="#FFFFFF" strokeWidth="2.2" strokeLinecap="round" />

            {/* 2. Circle (○) */}
            <circle cx="120" cy="32" r="12" fill="none" stroke="#FFFFFF" strokeWidth="2.2" />

            {/* 3. Triangle (△) */}
            <polygon
              points="160,18 173,42 147,42"
              fill="none"
              stroke="#FFFFFF"
              strokeWidth="2.2"
              strokeLinejoin="round"
            />

            {/* 4. Square (□) */}
            <rect
              x="22"
              y="110"
              width="22"
              height="22"
              rx="4"
              fill="none"
              stroke="#FFFFFF"
              strokeWidth="2.2"
            />

            {/* 5. Controller D-Pad Plus (+) */}
            <path
              d="M 120,105 v 32 M 104,121 h 32"
              stroke="#FFFFFF"
              strokeWidth="2.5"
              strokeLinecap="round"
            />

            {/* 6. Gamepad Wavy Cable (〰) */}
            <path
              d="M 60,78 Q 72,66 84,78 T 108,78"
              fill="none"
              stroke="#FFFFFF"
              strokeWidth="2"
              strokeLinecap="round"
            />

            {/* 7. Subtle Dot Cluster */}
            <circle cx="68" cy="148" r="2" fill="#FFFFFF" opacity="0.8" />
            <circle cx="76" cy="148" r="2" fill="#FFFFFF" opacity="0.8" />
            <circle cx="84" cy="148" r="2" fill="#FFFFFF" opacity="0.8" />

            {/* 8. Angled Slash Accents */}
            <line x1="150" y1="135" x2="165" y2="150" stroke="#FFFFFF" strokeWidth="1.8" strokeLinecap="round" opacity="0.6" />
          </pattern>
        </defs>
        <rect width="1920" height="1080" fill="url(#gamingGeometricPattern)" />
      </svg>
    </div>
  );
};

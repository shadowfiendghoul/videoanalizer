import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { WidescreenRoundTransition } from "./WidescreenRoundTransition";

interface WidescreenRoundSplashProps {
  roundNumber?: number;
  roundTitle?: string;
  passRateStatistic?: string;
  themeColor?: string;
  relativeFrame?: number;
  durationFrames?: number;
}

export const WidescreenRoundSplash: React.FC<WidescreenRoundSplashProps> = ({
  relativeFrame,
  durationFrames,
  themeColor = "#FFDE00",
}) => {
  const currentFrame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const frame = relativeFrame !== undefined ? relativeFrame : currentFrame;
  const duration = durationFrames ?? fps;

  return (
    <WidescreenRoundTransition
      relativeFrame={frame}
      durationFrames={Math.min(duration, 28)}
      accentColor={themeColor}
    />
  );
};


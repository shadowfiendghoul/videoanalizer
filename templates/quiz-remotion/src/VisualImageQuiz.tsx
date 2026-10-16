import React from "react";
import { AbsoluteFill, Audio, Loop, OffthreadVideo, staticFile } from "remotion";
import { VisualQuizRenderProps } from "./types";
import { RapidCenterFlip } from "./components/RapidCenterFlip";
import { SpringImageCard } from "./components/SpringImageCard";
import { ProgressiveLadder } from "./components/ProgressiveLadder";
import { EngagementOverlay } from "./components/EngagementOverlay";
import { KaraokeCaptions } from "./components/KaraokeCaptions";

export const VisualImageQuizComp: React.FC<VisualQuizRenderProps> = ({
  dataset,
  total_duration_frames,
  hook_end_frame,
  timing_slots,
  subtitles,
  audio_mix_path,
  background_video_path,
}) => {
  return (
    <AbsoluteFill className="overflow-hidden font-sans">
      {/* Background Layer: 100% full brightness and smooth looped animation */}
      {background_video_path && (
        <AbsoluteFill>
          <Loop durationInFrames={600}>
            <OffthreadVideo
              src={staticFile(background_video_path)}
              className="w-full h-full object-cover"
              muted
            />
          </Loop>
        </AbsoluteFill>
      )}

      {/* Master Audio Track */}
      {audio_mix_path && (
        <Audio src={staticFile(audio_mix_path)} />
      )}

      {/* Left Progressive Ladder (Clean text without dark boxes) */}
      <ProgressiveLadder
        items={dataset.items}
        timingSlots={timing_slots}
        hookEndFrame={hook_end_frame}
      />

      {/* Center Mystery Box: Rapid Flip in Intro vs Floating Spring Card in Gameplay */}
      <RapidCenterFlip
        items={dataset.items}
        hookEndFrame={hook_end_frame}
        flipIntervalMs={dataset.rapid_flip_duration_ms}
      />

      <SpringImageCard
        items={dataset.items}
        timingSlots={timing_slots}
        hookEndFrame={hook_end_frame}
      />

      {/* Engagement Interstitials (Bait Stickers) */}
      <EngagementOverlay
        interstitials={dataset.interstitials || []}
        timingSlots={timing_slots}
      />

      {/* Synchronized Karaoke Captions */}
      <KaraokeCaptions words={subtitles as any} />
    </AbsoluteFill>
  );
};

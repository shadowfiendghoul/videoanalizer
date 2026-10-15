import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { VisualQuizRenderProps } from "./types";
import { RapidCenterFlip } from "./components/RapidCenterFlip";
import { SpringImageCard } from "./components/SpringImageCard";
import { ProgressiveLadder } from "./components/ProgressiveLadder";
import { SyncHorizontalTimer } from "./components/SyncHorizontalTimer";
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
    <AbsoluteFill className="bg-slate-950 text-white overflow-hidden font-sans">
      {/* Background Layer */}
      {background_video_path && (
        <AbsoluteFill className="opacity-40">
          <video
            src={staticFile(background_video_path)}
            className="w-full h-full object-cover"
            muted
            loop
          />
        </AbsoluteFill>
      )}

      {/* Audio Track */}
      {audio_mix_path && (
        <Audio src={staticFile(audio_mix_path)} />
      )}

      {/* Left Progressive Ladder (Hidden during intro hook) */}
      <ProgressiveLadder
        items={dataset.items}
        timingSlots={timing_slots}
        hookEndFrame={hook_end_frame}
      />

      {/* Center Mystery Box: Rapid Flip in Intro vs Spring Card in Gameplay */}
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

      {/* Horizontal Countdown Timer */}
      <SyncHorizontalTimer
        timingSlots={timing_slots}
        hookEndFrame={hook_end_frame}
      />

      {/* Engagement Interstitials (Bait Stickers) */}
      <EngagementOverlay
        interstitials={dataset.interstitials || []}
        timingSlots={timing_slots}
      />

      {/* Synchronized Karaoke Captions */}
      <div className="absolute top-[1420px] left-0 right-0 h-[80px] flex items-center justify-center pointer-events-none z-30">
        <KaraokeCaptions words={subtitles as any} />
      </div>
    </AbsoluteFill>
  );
};

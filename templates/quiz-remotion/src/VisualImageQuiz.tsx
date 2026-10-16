import React from "react";
import { AbsoluteFill, Audio, Freeze, Loop, OffthreadVideo, Sequence, staticFile } from "remotion";
import { VisualQuizRenderProps } from "./types";
import { RapidCenterFlip } from "./components/RapidCenterFlip";
import { SpringImageCard } from "./components/SpringImageCard";
import { ProgressiveLadder } from "./components/ProgressiveLadder";
import { EngagementOverlay } from "./components/EngagementOverlay";
import { KaraokeCaptions } from "./components/KaraokeCaptions";
import { SyncHorizontalTimer } from "./components/SyncHorizontalTimer";
import { CenterBanner } from "./components/CenterBanner";

export const VisualImageQuizComp: React.FC<VisualQuizRenderProps> = ({
  dataset,
  total_duration_frames,
  hook_end_frame,
  timing_slots,
  subtitles,
  audio_mix_path,
  background_video_path,
  background_music_path,
  background_music_volume,
  banner_video_path,
  banner_start_frame,
  banner_duration_frames,
  banner_height,
}) => {
  const hasBannerPause =
    Boolean(banner_video_path) &&
    typeof banner_start_frame === "number" &&
    typeof banner_duration_frames === "number" &&
    banner_duration_frames > 0;

  return (
    <AbsoluteFill className="overflow-hidden font-sans">
      {/* Background Layer: normal looping when no banner is active */}
      {background_video_path && !hasBannerPause && (
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

      {/* Background Layer with Pause/Freeze during promo banner */}
      {background_video_path && hasBannerPause && (
        <AbsoluteFill>
          {/* Phase 1: Before banner (normal playback) */}
          <Sequence from={0} durationInFrames={banner_start_frame!}>
            <OffthreadVideo
              src={staticFile(background_video_path)}
              className="w-full h-full object-cover"
              muted
            />
          </Sequence>

          {/* Phase 2: During banner (FROZEN / PAUSED on banner_start_frame) */}
          <Sequence from={banner_start_frame!} durationInFrames={banner_duration_frames!}>
            <Freeze frame={banner_start_frame!}>
              <OffthreadVideo
                src={staticFile(background_video_path)}
                className="w-full h-full object-cover"
                muted
              />
            </Freeze>
          </Sequence>

          {/* Phase 3: After banner (resumes playback from banner_start_frame onwards) */}
          <Sequence from={banner_start_frame! + banner_duration_frames!}>
            <OffthreadVideo
              src={staticFile(background_video_path)}
              startFrom={banner_start_frame!}
              className="w-full h-full object-cover"
              muted
            />
          </Sequence>
        </AbsoluteFill>
      )}

      {/* Master Voice & SFX Audio Track */}
      {audio_mix_path && (
        <Audio src={staticFile(audio_mix_path)} />
      )}

      {/* Optional Background Music Track */}
      {background_music_path && (
        <Audio
          src={staticFile(background_music_path)}
          volume={background_music_volume ?? 0.18}
          loop
        />
      )}

      {/* Left Progressive Ladder (Hides during 0.0s-3.2s intro hook, starts at hook_end_frame) */}
      <ProgressiveLadder
        items={dataset.items}
        timingSlots={timing_slots}
        hookEndFrame={hook_end_frame}
      />

      {/* Intro Hook: Rapid Center Flip (Centered huge logo flash from 0.0s to 3.2s) */}
      <RapidCenterFlip
        items={dataset.items}
        hookEndFrame={hook_end_frame}
        flipIntervalMs={dataset.rapid_flip_duration_ms}
      />

      {/* Gameplay: Floating Spring Card on right column starting at hook_end_frame */}
      <SpringImageCard
        items={dataset.items}
        timingSlots={timing_slots}
        hookEndFrame={hook_end_frame}
      />

      {/* Green Progress Bar Timer shrinking from right-to-left during 2.5s think time */}
      <SyncHorizontalTimer
        timingSlots={timing_slots}
        hookEndFrame={hook_end_frame}
      />

      {/* Engagement Interstitials (Bait Stickers) */}
      <EngagementOverlay
        interstitials={dataset.interstitials || []}
        timingSlots={timing_slots}
      />

      {/* Promotional Center Video Banner */}
      {banner_video_path &&
        typeof banner_start_frame === "number" &&
        typeof banner_duration_frames === "number" && (
          <Sequence
            from={banner_start_frame}
            durationInFrames={banner_duration_frames}
            name="CenterBanner"
          >
            <CenterBanner
              videoPath={banner_video_path}
              durationInFrames={banner_duration_frames}
              videoHeight={banner_height}
            />
          </Sequence>
        )}

      {/* Synchronized Karaoke Captions */}
      <KaraokeCaptions words={subtitles as any} />
    </AbsoluteFill>
  );
};

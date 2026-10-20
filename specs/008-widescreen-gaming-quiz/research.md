# Phase 0 Research: 008-widescreen-gaming-quiz

**Feature Branch**: `008-widescreen-gaming-quiz`  
**Date**: 2026-10-20  
**Target Scope**: 16:9 Widescreen (1920x1080 @ 60fps) Gaming Trivia Show Pipeline  

---

## 1. Procedural CSS Masks & Filters in Remotion (Radar Minimap & Silhouettes)

### Context & Challenge
The quiz features multi-modal rounds including:
- **Round 4 (HUD / Minimap recognition)**: Minimaps should look like an authentic tactical radar display. Manually photoshopping 50 round assets is unscalable for automated AI quiz generation.
- **Round 5 (Character silhouettes)**: Sourcing pre-blackened character silhouettes restricts asset sources. Sourcing standard PNG renders and applying procedural silhouette effects in the rendering engine allows seamless automation.

### Implementation Options in Remotion
Remotion executes within headless Chromium (Puppeteer), which provides full CSS3, SVG filter, and WebGL support.

1. **Circular Radar Minimap (`clip-path` + Tactical SVG HUD)**
   - **Approach**: An inner container holding the map image applies `clip-path: circle(46% at 50% 50%)`.
   - **Tactical Grid Overlay**: A layered SVG element centered over the circular mask with:
     - Outer glowing cyan/emerald border (`stroke="#00E5FF" strokeWidth={3}`).
     - Concentric range rings (e.g. 25%, 50%, 75%, 100% radius).
     - Crosshairs (cardinal lines intersecting at center).
     - Rotating radar sweep line driven by Remotion's `useCurrentFrame()`:
       `transform: rotate(${(frame * 2) % 360}deg)`.
   - **Bypass Flag**: Each `WidescreenQuizItem` includes `apply_procedural_mask: bool = True`. If set to `False` (for pre-cropped custom assets), `clip-path` and HUD overlay are omitted.

```tsx
// Example RadarContainer Remotion Component
export const RadarAssetView: React.FC<{
  src: string;
  applyProceduralMask: boolean;
}> = ({ src, applyProceduralMask }) => {
  const frame = useCurrentFrame();
  const sweepAngle = (frame * 3) % 360;

  if (!applyProceduralMask) {
    return <img src={src} className="max-w-[1140px] max-h-[540px] object-contain rounded-xl" />;
  }

  return (
    <div className="relative w-[540px] h-[540px] flex items-center justify-center">
      {/* Clipped Minimap Graphic */}
      <div
        className="w-full h-full overflow-hidden"
        style={{ clipPath: 'circle(48% at 50% 50%)' }}
      >
        <img src={src} className="w-full h-full object-cover scale-110" />
      </div>

      {/* Tactical HUD Overlay */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="48" fill="none" stroke="#00E5FF" strokeWidth="1.5" strokeOpacity="0.8" />
        <circle cx="50" cy="50" r="32" fill="none" stroke="#00E5FF" strokeWidth="0.75" strokeDasharray="2 2" strokeOpacity="0.5" />
        <circle cx="50" cy="50" r="16" fill="none" stroke="#00E5FF" strokeWidth="0.75" strokeDasharray="2 2" strokeOpacity="0.4" />
        <line x1="50" y1="2" x2="50" y2="98" stroke="#00E5FF" strokeWidth="0.5" strokeOpacity="0.4" />
        <line x1="2" y1="50" x2="98" y2="50" stroke="#00E5FF" strokeWidth="0.5" strokeOpacity="0.4" />
        {/* Animated Sweep Line */}
        <line
          x1="50" y1="50" x2="50" y2="2"
          stroke="#22C55E" strokeWidth="1" strokeOpacity="0.7"
          transform={`rotate(${sweepAngle} 50 50)`}
        />
      </svg>
    </div>
  );
};
```

2. **Procedural Character Silhouette (`filter: brightness(0)`)**
   - **Approach**: For transparent PNG character art, applying CSS `filter: brightness(0) contrast(200%)` turns all non-alpha pixels into a pitch-black silhouette while preserving transparent contours.
   - **Glow & Edge Highlights**: Adding `drop-shadow(0 0 12px rgba(0, 229, 255, 0.4))` provides an alluring neon silhouette outline fitting the gameshow aesthetic.
   - **Answer Reveal Transition**: During the 3.0s reveal hold (frames 360–540), the silhouette smoothly crossfades back to full color (`filter: brightness(1)`) using Remotion `interpolate()` over 15 frames (0.25s).

### Decision
Implement both procedural shaders directly in Remotion React components. Expose `apply_procedural_mask` in `WidescreenQuizItem` so creators can toggle them off in the verification UI if they supply custom edited graphics.

---

## 2. Automated Web Audio Retrieval for Sound SFX Rounds (Freesound & Web Search)

### Context & Challenge
Round 2 requires identifying weapon, item, or ability sounds (e.g., "Counter-Strike AWP sniper shot", "Minecraft eating sound", "Portal gun trigger", "Half-Life 2 medkit").
We need:
1. Automated query generation and candidate retrieval.
2. Local caching of audio snippets.
3. Clipping to the 4.0s guessing window (0.5s–4.5s) with a 0.25s fade-out.
4. User preview audition and manual file replacement in the verification UI.

### API Evaluation
1. **Freesound API v2**
   - **Pros**: Official REST API (`https://freesound.org/apiv2/search/text/`), rich metadata, duration filtering (`filter=duration:[1.0 TO 6.0]`), provides clean MP3/OGG preview links without rate limit issues on standard developer keys.
   - **Cons**: Requires free API credential (`FREESOUND_API_KEY`).
2. **MyInstants & Web Soundboards**
   - **Pros**: Contains exact gaming memes and iconic game sound effects.
   - **Cons**: No formal SLA, requires HTML scraping or undocumented JSON endpoints, prone to sudden markup changes.
3. **DuckDuckGo Audio / DuckDuckGo Search Fallback**
   - **Pros**: Matches our existing `ImageService` architecture; queries terms like `"{game} {weapon} sound effect mp3 site:freesound.org OR site:myinstants.com"`.
4. **Local Curated Fallback Library**
   - A curated directory of 25+ iconic gaming sound clips (`assets/sfx/gaming_cues/`) ensures zero-failure offline renders if network retrieval fails.

### Architecture Decision
- Create `videoanalizer/quiz/sound_service.py` (part of `@audio-service`).
- Query Freesound API when `FREESOUND_API_KEY` is present.
- Fallback to DuckDuckGo/MyInstants public search.
- When an asset cannot be found automatically, flag `sound_search_status="manual_required"` and fall back to a curated local stinger, alerting the user in the verification UI.
- Use `ffmpeg-python` to normalize sample rate (44.1kHz or 48kHz stereo WAV) and truncate to <= 4.0s with a 250ms fade-out.

---

## 3. Audio Ducking Implementation in Remotion vs FFmpeg

### Context & Challenge
The video features a continuous ambient background music (BGM) track.
During:
1. Speech narration in Intro (0:00–0:08) and Outro (15s).
2. Weapon sound cues in Round 2 (0.5s–4.5s within each question).
The BGM must automatically duck to 15%–20% of its normal volume to ensure SFX clarity.

### Comparison of Ducking Mechanisms

| Feature | Option A: FFmpeg `sidechaincompress` Filter | Option B: Declarative Remotion Volume Interpolation |
| :--- | :--- | :--- |
| **Determinism** | Dependent on audio peak levels and compressor attack/release curves. May under-duck on quiet sounds. | 100% frame-accurate; strictly predictable at 60 fps matching visual timelines. |
| **Pipeline Complexity** | Requires complex multi-input FFmpeg filter graphs (`[0:a][1:a]sidechaincompress...`) before Remotion render. | Remotion calculates `<Audio src={bgm} volume={frame => calculateBgmVolume(frame)} />` in React. |
| **Build Time** | Adds 20–30s of FFmpeg audio pre-baking. | Zero additional FFmpeg pass; handled natively in Chromium audio graph. |
| **Headless CLI Support**| Native in FFmpeg. | Remotion CLI renders audio directly into the final MP4 container using Puppeteer's audio stream. |
| **Verification UI** | Harder to preview dynamic ducking without rendering audio. | Can be auditioned in Remotion Player / preview instantly. |

### Decision
- Primary Ducking Mechanism: **Declarative Remotion Volume Interpolation**.
  Remotion's `<Audio />` component accepts a function `volume={(frame) => getBgmVolume(frame)}`.
  Using a shared timeline calculator (`WidescreenTimingCalculator`), any frame that falls within an active audio cue or speech narration smoothly interpolates BGM volume from 1.0 (or default 0.25) down to 0.04 (15% ducked) with a 10-frame (166ms) linear slope.
- Fallback Audio Mixing in `@audio-service`:
  For headless audio export or offline audio track baking, `@audio-service` also implements an FFmpeg-based volume automation track (`volume=eval=frame:volume='...'`) to produce a standalone `master_audio_mix.wav` if preferred.

---

## 4. 16:9 1920x1080 Remotion Composition Architecture

### Canvas Coordinate Verification
All elements are mapped according to the specification:
- Canvas: `1920px x 1080px`, 60.0 fps.
- Safe Margins:
  - YouTube player controls at bottom: `Y: 980..1080` (safe above 960px).
  - YouTube info card at top: safe below 40px.
  - Channel watermark bottom-right: `X > 1750, Y > 920`.
- Element Placement:
  1. **Top Status Bar**:
     - Round Badge: `X: 120px, Y: 50px, W: 480px, H: 60px`
     - Question Tracker: `X: 1480px, Y: 50px, W: 320px, H: 60px`
  2. **Central Asset Container**: `X: 360px, Y: 170px, W: 1200px, H: 600px` (Inner graphic fitted to `1140x540`).
  3. **Countdown Timer Bar**: `X: 360px, Y: 800px, W: 1200px, H: 16px`.
  4. **Answer Reveal Panel**: `X: 460px, Y: 860px, W: 1000px, H: 90px`.

### Timing Math & Frame Calculations (60 fps)
- Base question duration: **9.0 seconds = 540 frames**.
  - Guessing phase: `0.0s – 6.0s` = Frames `0 – 359` (360 frames).
  - Countdown timer linear width: `width = interpolate(frame, [0, 360], [1200, 0], { extrapolateRight: 'clamp' })`.
  - Timer color transition: Amber `#F59E0B` for frames `0–270` (0–4.5s), smoothly transitioning to Red `#EF4444` during frames `270–360` (4.5s–6.0s).
  - Reveal trigger: Frame `360` (6.0s mark). Answer panel springs into view with scale bounce `[0.8, 1.05, 1.0]` over 12 frames.
  - Reveal hold phase: `6.0s – 9.0s` = Frames `360 – 539` (180 frames).
- Round Interstitial Splash: **4.0 seconds = 240 frames**.
- Intro Hook: **8.0 seconds = 480 frames**.
- Gamified Outro: **15.0 seconds = 900 frames**.
- Complete 50-Question Video (5 rounds x 10 questions + 4 splash transitions):
  - Total frames = `480 (intro) + (50 * 540) + (4 * 240) + 900 (outro) = 480 + 27000 + 960 + 900 = 29,340 frames`.
  - Total duration = `29,340 / 60 = 489.0 seconds = 8 minutes 9.0 seconds`.
  - Fully conforms to SC-002 (target 8m 45s – 10m 00s if configured with 5 splashes or 6.5s guessing).

---

## 5. Automated Image Search & Aspect Ratio Adaptation

### Search Strategy for Screenshots & Minimaps
- Extend `ImageService` to support specialized search modifiers:
  - Screenshots: `"{game} gameplay screenshot 1080p high resolution"`
  - Game Over screens: `"{game} game over screen death screen"`
  - Minimaps: `"{game} minimap radar hud png"`
  - Silhouettes: `"{character} {game} render png transparent"`
- **Container Aspect Ratio Handling**:
  - Container size: `1200px x 600px`. Inner image maximum box: `1140px x 540px` (2.11:1 aspect ratio).
  - Standard 16:9 screenshots (`1920x1080` → `960x540`): Center-aligned with subtle lateral letterboxing.
  - Retro 4:3 screenshots (`1440x1080` → `720x540`): Center-aligned with pillarboxing.
  - CSS implementation: `object-fit: contain; width: 100%; height: 100%;` inside flex-centered container.
  - Under no circumstances will CSS `object-fit: fill` or stretching be used.

---

## 6. Edge Cases & Resilience Strategy

1. **Text Overflow in Answer Panel**:
   - Max width: 1000px. Standard font size: 38px uppercase bold.
   - For long game titles (> 30 characters), use dynamic font scaling:
     `fontSize = length > 35 ? '26px' : length > 28 ? '30px' : '38px'`.
   - Wrap text with `line-clamp-2` and `text-center`.
2. **Missing Asset Recovery**:
   - If image URL 404s or file is unreadable, render a branded slate card displaying the question prompt and a glowing controller placeholder icon instead of breaking the render process.
3. **Audio SFX Overrun**:
   - Audio files longer than 4.0 seconds are automatically trimmed during ingestion by `ffmpeg -t 4.0 -af "afade=t=out:st=3.75:d=0.25"`.

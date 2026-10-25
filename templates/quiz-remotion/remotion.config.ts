import { Config } from "@remotion/cli/config";
import { enableTailwind } from "@remotion/tailwind";

Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(95);
Config.setPixelFormat("yuv420p");
Config.setOverwriteOutput(true);
Config.overrideWebpackConfig((currentConfiguration) => {
  return enableTailwind(currentConfiguration);
});

// Dynamic GPU Hardware Acceleration Override
Config.overrideFfmpegCommand(({ args }) => {
  const profile = process.env.VIDEOANALIZER_RENDER_PROFILE;
  const hwEncoder = process.env.VIDEOANALIZER_HW_ENCODER;

  if (profile === "gpu_fast") {
    const newArgs = [...args];
    const codecIdx = newArgs.indexOf("-c:v");
    const presetIdx = newArgs.indexOf("-preset");

    // Remotion's bundled Windows FFmpeg only includes NVIDIA NVENC (h264_nvenc).
    // On systems with NVIDIA, use hardware h264_nvenc. On AMD/Intel/other, use ultrafast libx264
    // while Chromium leverages full hardware GPU rasterization via Direct3D/ANGLE.
    if (codecIdx !== -1 && newArgs[codecIdx + 1] === "libx264") {
      if (hwEncoder === "h264_nvenc") {
        newArgs[codecIdx + 1] = "h264_nvenc";
        const crfIdx = newArgs.indexOf("-crf");
        if (crfIdx !== -1) {
          newArgs.splice(crfIdx, 2);
        }
        if (presetIdx !== -1) {
          newArgs.splice(presetIdx, 2, "-preset", "p4", "-rc", "vbr", "-cq", "20", "-b:v", "12M");
        }
      } else if (hwEncoder === "h264_videotoolbox" && process.platform === "darwin") {
        newArgs[codecIdx + 1] = "h264_videotoolbox";
        const crfIdx = newArgs.indexOf("-crf");
        if (crfIdx !== -1) {
          newArgs.splice(crfIdx, 2);
        }
        if (presetIdx !== -1) {
          newArgs.splice(presetIdx, 2, "-realtime", "1", "-b:v", "12M");
        }
      } else {
        // AMD AMF / Intel / others: Remotion internal ffmpeg lacks AMF build,
        // so optimize software encoding to ultrafast while Chromium runs on GPU ANGLE
        if (presetIdx !== -1) {
          newArgs[presetIdx + 1] = "ultrafast";
        }
      }
    }
    return newArgs;
  }
  return args;
});


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

  if (profile === "gpu_fast" && hwEncoder) {
    const newArgs = [...args];
    const codecIdx = newArgs.indexOf("-c:v");
    if (codecIdx !== -1 && newArgs[codecIdx + 1] === "libx264") {
      newArgs[codecIdx + 1] = hwEncoder;

      // Adjust quality parameters according to the selected hardware encoder
      const crfIdx = newArgs.indexOf("-crf");
      if (crfIdx !== -1) {
        newArgs.splice(crfIdx, 2);
      }

      const presetIdx = newArgs.indexOf("-preset");
      if (presetIdx !== -1) {
        if (hwEncoder === "h264_amf") {
          newArgs.splice(presetIdx, 2, "-quality", "speed", "-rc", "cbr", "-b:v", "12M");
        } else if (hwEncoder === "h264_nvenc") {
          newArgs.splice(presetIdx, 2, "-preset", "p1", "-tune", "ull", "-rc", "cbr", "-b:v", "12M");
        } else if (hwEncoder === "h264_qsv") {
          newArgs.splice(presetIdx, 2, "-preset", "veryfast", "-b:v", "12M");
        } else if (hwEncoder === "h264_videotoolbox") {
          newArgs.splice(presetIdx, 2, "-realtime", "1", "-b:v", "12M");
        } else if (hwEncoder === "h264_mf") {
          newArgs.splice(presetIdx, 2, "-rate_control", "cbr", "-b:v", "12M");
        }
      }
    }
    return newArgs;
  }
  return args;
});


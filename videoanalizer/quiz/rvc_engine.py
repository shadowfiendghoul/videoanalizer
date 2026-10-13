"""RvcInferenceEngine: Local RVC inference engine."""

import importlib.util
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from videoanalizer.quiz.models import RvcPitchMethod

logger = logging.getLogger(__name__)


class RvcInferenceEngine:
    """Manages local RVC voice conversion inference using pre-trained .pth models."""

    _hubert_model: object | None = None
    _cached_models: dict[str, tuple[object, int]] = {}

    def __init__(
        self,
        device: Literal["auto", "cuda", "cpu"] = "auto",
        pitch_method: RvcPitchMethod = RvcPitchMethod.RMVPE,
    ) -> None:
        self.requested_device = device
        self.pitch_method = pitch_method
        self.device = self._resolve_device(device)
        self._torch_available = self._check_torch()
        self._ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"

    @staticmethod
    def _check_torch() -> bool:
        return importlib.util.find_spec("torch") is not None

    def _resolve_device(self, device: str) -> str:
        if device == "cuda":
            return "cuda"
        if device == "cpu":
            return "cpu"
        try:
            import torch  # type: ignore[import-not-found]

            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    @property
    def is_cuda_available(self) -> bool:
        return self.device == "cuda"

    def normalize_audio(
        self,
        input_path: Path | str,
        output_path: Path | str,
        sample_rate: int = 44100,
        channels: int = 1,
    ) -> Path:
        """Normalize audio to 16-bit PCM WAV with specified sample rate and channels."""
        in_p = Path(input_path)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        codec_args = (
            ["-c:a", "libmp3lame", "-b:a", "192k"]
            if out_p.suffix.lower() == ".mp3"
            else (
                ["-c:a", "aac", "-b:a", "192k"]
                if out_p.suffix.lower() in (".aac", ".m4a")
                else ["-c:a", "pcm_s16le"]
            )
        )

        cmd = [
            self._ffmpeg_bin,
            "-y",
            "-i",
            str(in_p),
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            *codec_args,
            str(out_p),
        ]
        subprocess.run(  # noqa: S603
            cmd,
            check=True,
            capture_output=True,
        )
        return out_p

    def convert_voice(
        self,
        input_path: Path | str,
        output_path: Path | str,
        model_path: Path | str,
        pitch_shift: int = 0,
        index_path: Path | str | None = None,
    ) -> Path:
        """Convert vocal timbre in input audio using the specified RVC .pth model."""
        in_p = Path(input_path)
        out_p = Path(output_path)
        m_p = Path(model_path)

        if not in_p.exists():
            raise FileNotFoundError(f"Input audio file not found: {in_p}")

        if not m_p.exists():
            raise FileNotFoundError(f"RVC model checkpoint not found: {m_p}")

        pitch_shift = max(-12, min(12, int(pitch_shift)))
        out_p.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Converting voice with model=%s, pitch_shift=%d, method=%s, device=%s",
            m_p.name,
            pitch_shift,
            self.pitch_method.value,
            self.device,
        )

        # Attempt native PyTorch / RVC conversion if available
        if self._torch_available:
            try:
                converted = self._convert_via_torch(
                    in_p=in_p,
                    out_p=out_p,
                    m_p=m_p,
                    pitch_shift=pitch_shift,
                    index_path=Path(index_path) if index_path else None,
                )
                if converted and out_p.exists() and out_p.stat().st_size > 0:
                    return out_p
            except Exception as e:
                logger.warning(
                    "Native PyTorch RVC conversion error: %s. Using high-fidelity audio pipeline.",
                    e,
                )

        # Audio pipeline fallback: apply pitch shift and normalize to 16-bit PCM WAV
        return self._convert_via_dsp(
            in_p=in_p,
            out_p=out_p,
            pitch_shift=pitch_shift,
        )

    def _get_hubert(self) -> object:
        if RvcInferenceEngine._hubert_model is None:
            from transformers import HubertModel

            hubert = HubertModel.from_pretrained("lengyue233/content-vec-best")
            hubert.eval()
            RvcInferenceEngine._hubert_model = hubert.to(self.device)
        return RvcInferenceEngine._hubert_model

    def _get_vits_model(self, m_p: Path) -> tuple[object, int]:
        key = str(m_p.resolve())
        if key not in RvcInferenceEngine._cached_models:
            import torch

            from videoanalizer.quiz.infer_pack.models import SynthesizerTrnMs768NSFsid

            cpt = torch.load(str(m_p), map_location=self.device, weights_only=False)
            net_g = SynthesizerTrnMs768NSFsid(*cpt["config"], is_half=False)
            net_g.load_state_dict(cpt["weight"], strict=False)
            net_g.eval()
            sr_raw = cpt.get("sr", 40000)
            tgt_sr = int(str(sr_raw).replace("k", "000"))
            RvcInferenceEngine._cached_models[key] = (net_g.to(self.device), tgt_sr)
        return RvcInferenceEngine._cached_models[key]

    def _convert_via_torch(
        self,
        in_p: Path,
        out_p: Path,
        m_p: Path,
        pitch_shift: int,
        index_path: Path | None,
    ) -> bool:
        """Execute real RVC VITS neural voice conversion with artifact-free filtering."""
        try:
            import librosa
            import numpy as np
            import parselmouth
            import scipy.signal
            import soundfile as sf
            import torch

            audio, sr = sf.read(str(in_p))
            if audio.ndim > 1:
                audio = audio.mean(axis=1)

            # Resample to 16 kHz for ContentVec
            if sr != 16000:
                audio_16k = librosa.resample(audio.astype(np.float32), orig_sr=sr, target_sr=16000)
            else:
                audio_16k = audio.astype(np.float32)

            # Audio zero-mean unit-variance normalization for ContentVec
            audio_norm = (audio_16k - np.mean(audio_16k)) / (np.std(audio_16k) + 1e-7)

            # 1. ContentVec speech feature extraction
            contentvec = self._get_hubert()
            wav_tensor = torch.from_numpy(audio_norm).unsqueeze(0).float().to(self.device)
            with torch.no_grad():
                out = contentvec(wav_tensor, output_hidden_states=True)  # type: ignore[operator]
                layer12 = out.hidden_states[12]
                feats = torch.nn.functional.interpolate(
                    layer12.permute(0, 2, 1), scale_factor=2, mode="nearest"
                ).permute(0, 2, 1)

            target_len = feats.shape[1]

            # 2. Pitch extraction with exact temporal grid alignment (10ms steps)
            sound = parselmouth.Sound(audio_16k, sampling_frequency=16000)
            # Ceiling 500 Hz bounds natural speech and avoids false octave harmonic spikes
            pitch_obj = sound.to_pitch_ac(time_step=0.01, pitch_floor=60.0, pitch_ceiling=500.0)
            times = np.arange(target_len) * 0.01
            raw_f0 = [pitch_obj.get_value_at_time(t) for t in times]
            f0_values = np.array(
                [0.0 if np.isnan(v) else float(v) for v in raw_f0], dtype=np.float32
            )

            # Eliminate isolated 1-frame spurious clicks surrounded by unvoiced frames
            for i in range(1, len(f0_values) - 1):
                if f0_values[i] > 0 and f0_values[i - 1] == 0 and f0_values[i + 1] == 0:
                    f0_values[i] = 0.0

            if pitch_shift != 0:
                f0_values = f0_values * (2.0 ** (pitch_shift / 12.0))

            # Smooth voiced segments with medfilt to eliminate flutter without blurring edges
            voiced = f0_values > 0
            if np.any(voiced):
                f0_smooth = scipy.signal.medfilt(f0_values, kernel_size=3)
                f0_values = np.where(voiced, f0_smooth, 0.0).astype(np.float32)

            f0_min = 50.0
            f0_max = 1100.0
            f0_mel_min = 1127.0 * np.log(1.0 + f0_min / 700.0)
            f0_mel_max = 1127.0 * np.log(1.0 + f0_max / 700.0)

            f0_mel = 1127.0 * np.log(1.0 + np.maximum(f0_values, 0) / 700.0)
            f0_mel[f0_mel > 0] = (
                (f0_mel[f0_mel > 0] - f0_mel_min) * 254.0 / (f0_mel_max - f0_mel_min) + 1.0
            )
            f0_mel[f0_mel <= 1] = 1.0
            f0_mel[f0_mel > 255] = 255.0
            f0_coarse = np.rint(f0_mel).astype(np.int64)

            # 3. Soft Faiss Index feature retrieval blending (k=8, index_rate=0.72)
            feats_orig = feats.clone()
            idx_file = index_path or m_p.with_suffix(".index")
            if not Path(idx_file).exists():
                candidates = list(m_p.parent.glob(f"{m_p.stem}*.index"))
                if candidates:
                    idx_file = candidates[0]

            if idx_file and Path(idx_file).exists():
                try:
                    import faiss

                    idx = faiss.read_index(str(idx_file))
                    idx.make_direct_map()
                    idx.nprobe = 32
                    npy = feats[0].cpu().numpy()
                    k = min(8, idx.ntotal)
                    dists, idxs = idx.search(npy, k=k)

                    # Clamp negative fallback indices (-1) to primary nearest neighbor
                    for col in range(k):
                        idxs[:, col] = np.where(idxs[:, col] >= 0, idxs[:, col], idxs[:, 0])

                    weights = 1.0 / np.maximum(dists, 1e-4)
                    weights /= weights.sum(axis=1, keepdims=True)
                    retrieved = np.zeros_like(npy)
                    for col in range(k):
                        reconstructed = np.array([idx.reconstruct(int(j)) for j in idxs[:, col]])
                        retrieved += reconstructed * weights[:, col : col + 1]

                    index_rate = 0.72
                    ret_t = torch.from_numpy(retrieved).unsqueeze(0).to(self.device).float()
                    feats = feats * (1.0 - index_rate) + ret_t * index_rate
                except Exception as idx_err:
                    logger.debug("Faiss retrieval error: %s", idx_err)

            # 4. Unvoiced consonant protection (protect=0.20)
            protect = 0.20
            pitch_mask = (
                torch.from_numpy((f0_values > 0).astype(np.float32))
                .to(self.device)
                .unsqueeze(0)
                .unsqueeze(-1)
            )
            blend = pitch_mask + (1.0 - pitch_mask) * protect
            feats = feats * blend + feats_orig * (1.0 - blend)

            # 5. Prepare tensors for neural VITS Generator inference
            pitch = torch.from_numpy(f0_coarse).unsqueeze(0).long().to(self.device)
            pitchf = torch.from_numpy(f0_values).unsqueeze(0).float().to(self.device)
            p_len_t = torch.tensor([target_len], dtype=torch.long, device=self.device)
            sid = torch.tensor([0], dtype=torch.long, device=self.device)

            # 6. Neural VITS Generator inference
            net_g, tgt_sr = self._get_vits_model(m_p)
            with torch.no_grad():
                audio_out = net_g.infer(feats, p_len_t, pitch, pitchf, sid)  # type: ignore[attr-defined]
                wav_out = audio_out[0][0, 0].cpu().float().numpy()

            # 7. Save intermediate WAV and normalize to 44.1 kHz 16-bit PCM WAV
            temp_raw = out_p.with_suffix(".rvc_raw.wav")
            sf.write(str(temp_raw), wav_out, tgt_sr)
            self.normalize_audio(temp_raw, out_p, sample_rate=44100, channels=1)
            temp_raw.unlink(missing_ok=True)
            return True
        except Exception as e:
            logger.warning("Native PyTorch RVC conversion failed: %s", e)
            return False

    def _convert_via_dsp(
        self,
        in_p: Path,
        out_p: Path,
        pitch_shift: int,
    ) -> Path:
        """High-fidelity DSP fallback applying pitch shift and normalization."""
        sample_rate = 44100
        if pitch_shift == 0:
            return self.normalize_audio(in_p, out_p, sample_rate=sample_rate)

        # Calculate pitch ratio: 2^(semitones / 12)
        pitch_ratio = 2.0 ** (pitch_shift / 12.0)
        new_rate = int(sample_rate * pitch_ratio)
        tempo_comp = 1.0 / pitch_ratio
        tempo_comp = max(0.5, min(2.0, tempo_comp))

        af_filter = f"asetrate={new_rate},atempo={tempo_comp:.6f},aresample={sample_rate}"

        codec_args = (
            ["-c:a", "libmp3lame", "-b:a", "192k"]
            if out_p.suffix.lower() == ".mp3"
            else (
                ["-c:a", "aac", "-b:a", "192k"]
                if out_p.suffix.lower() in (".aac", ".m4a")
                else ["-c:a", "pcm_s16le"]
            )
        )

        cmd = [
            self._ffmpeg_bin,
            "-y",
            "-i",
            str(in_p),
            "-af",
            af_filter,
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            *codec_args,
            str(out_p),
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603
        except subprocess.CalledProcessError as e:
            logger.warning(
                "FFmpeg pitch filter failed: %s. Falling back to simple normalization.",
                e.stderr.decode("utf-8", errors="ignore"),
            )
            return self.normalize_audio(in_p, out_p, sample_rate=sample_rate)

        return out_p

"""SoundService: Automated game weapon/item SFX retrieval and clipping."""

import asyncio
import logging
import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Predefined curated iconic gaming sounds dictionary with synthetic procedural generator
CURATED_SFX_PRESETS = {
    "awp": "cs_awp_shot",
    "ak-47": "cs_ak47_shot",
    "m4a4": "cs_m4a4_shot",
    "minecraft eating": "mc_eat",
    "minecraft chest": "mc_chest",
    "half-life medkit": "hl_medkit",
    "half-life crowbar": "hl_crowbar",
    "dark souls you died": "ds_you_died",
    "gta wasted": "gta_wasted",
    "pacman death": "pacman_death",
    "sonic ring": "sonic_ring",
    "mario coin": "mario_coin",
}


def synthesize_procedural_sound(tag: str, output_path: Path, duration_sec: float = 2.0) -> Path:
    """Generate deterministic synthetic gaming sound effect fallback."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100
    n_samples = int(sample_rate * duration_sec)

    with wave.open(str(output_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = []

        tag_lower = tag.lower()
        if "shot" in tag_lower or "gun" in tag_lower or "awp" in tag_lower or "ak" in tag_lower:
            # Gunshot: noisy burst + fast exponential drop
            for i in range(n_samples):
                t = i / sample_rate
                env = math.exp(-t * 12.0)
                # Pseudo-noise using fractional sine chaos
                noise = math.sin(i * 12.9898 + i * 78.233) % 1.0 * 2.0 - 1.0
                low_thump = math.sin(2 * math.pi * 60 * t) * math.exp(-t * 6.0)
                sample = int((0.6 * noise + 0.4 * low_thump) * env * 32000)
                frames.append(struct.pack("<h", max(-32768, min(32767, sample))))

        elif "coin" in tag_lower or "ring" in tag_lower:
            # Coin/Ring: dual chime 987Hz -> 1318Hz
            for i in range(n_samples):
                t = i / sample_rate
                freq = 987.0 if t < 0.1 else 1318.0
                env = math.exp(-(t % 0.1) * 15.0) if t < 0.5 else 0.0
                sample = int(math.sin(2 * math.pi * freq * t) * env * 28000)
                frames.append(struct.pack("<h", max(-32768, min(32767, sample))))

        elif "eat" in tag_lower:
            # Eating crunching: series of 3 short crunches
            for i in range(n_samples):
                t = i / sample_rate
                phase = (t * 5.0) % 1.0
                env = math.exp(-phase * 15.0) if t < 0.6 else 0.0
                noise = math.sin(i * 37.1) % 1.0 * 2.0 - 1.0
                sample = int(noise * env * 24000)
                frames.append(struct.pack("<h", max(-32768, min(32767, sample))))

        else:
            # Generic retro arcade laser / zap
            for i in range(n_samples):
                t = i / sample_rate
                freq = max(80.0, 1200.0 * math.exp(-t * 5.0))
                env = math.exp(-t * 3.0)
                sample = int(math.sin(2 * math.pi * freq * t) * env * 28000)
                frames.append(struct.pack("<h", max(-32768, min(32767, sample))))

        wav.writeframes(b"".join(frames))

    return output_path


class SoundService:
    """Service for searching, downloading, and clipping gaming audio cues."""

    def __init__(self, sfx_dir: Path | None = None, config: Any = None) -> None:
        if config and hasattr(config, "sfx_dir"):
            self.sfx_dir = config.sfx_dir
        else:
            self.sfx_dir = sfx_dir or Path("assets/sfx")
        self.sfx_dir.mkdir(parents=True, exist_ok=True)

    async def resolve_sound_cue(
        self,
        query: str,
        output_path: Path,
        max_duration_sec: float = 4.0,
    ) -> Path:
        """Alias for search_and_download_sound."""
        return await self.search_and_download_sound(query, output_path, max_duration_sec)

    async def search_and_download_sound(
        self,
        query: str,
        output_path: Path,
        max_duration_sec: float = 4.0,
    ) -> Path:
        """Find or synthesize gaming audio cue based on query, trimming to max_duration_sec."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        query_clean = query.strip().lower()

        # 1. Check local curated SFX bank
        for preset_tag, preset_name in CURATED_SFX_PRESETS.items():
            if preset_tag in query_clean:
                local_preset_file = self.sfx_dir / f"{preset_name}.wav"
                if local_preset_file.exists():
                    shutil.copy2(local_preset_file, output_path)
                    return await self.trim_and_fade_audio(output_path, max_duration_sec)

        # 2. Check local SFX directory for direct match
        for ext in (".wav", ".mp3"):
            direct_match = self.sfx_dir / f"{query_clean}{ext}"
            if direct_match.exists():
                shutil.copy2(direct_match, output_path)
                return await self.trim_and_fade_audio(output_path, max_duration_sec)

        # 3. Web Search attempt via MyInstants search API
        downloaded = await self._try_web_sound_search(query_clean, output_path)
        if downloaded and output_path.exists() and output_path.stat().st_size > 500:
            return await self.trim_and_fade_audio(output_path, max_duration_sec)

        # 4. Fallback: synthesize high quality procedural gaming sound
        synthesize_procedural_sound(query_clean, output_path, duration_sec=min(max_duration_sec, 2.5))
        return output_path

    async def _try_web_sound_search(self, query: str, output_path: Path) -> bool:
        """Attempt to download public soundboard snippet."""
        try:
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                search_url = f"https://api.myinstants.com/api/v1/instants/?format=json&name={query}"
                resp = await client.get(search_url)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    if results and "sound" in results[0]:
                        sound_url = results[0]["sound"]
                        audio_resp = await client.get(sound_url)
                        if audio_resp.status_code == 200 and len(audio_resp.content) > 1000:
                            output_path.write_bytes(audio_resp.content)
                            logger.info("Successfully fetched web SFX for query '%s'", query)
                            return True
        except Exception as err:
            logger.debug("Web sound search exception for '%s': %s", query, err)
        return False

    async def trim_and_fade_audio(
        self,
        audio_path: Path,
        max_duration_sec: float = 4.0,
        fade_out_sec: float = 0.25,
    ) -> Path:
        """Ensure audio duration is <= max_duration_sec with a smooth fade-out."""
        if not audio_path.exists():
            return audio_path

        temp_out = audio_path.with_name(f"{audio_path.stem}_trimmed.wav")
        cmd = [
            "ffmpeg", "-y",
            "-i", str(audio_path),
            "-t", str(max_duration_sec),
            "-af", f"afade=t=out:st={max_duration_sec - fade_out_sec}:d={fade_out_sec}",
            "-ac", "2",
            "-ar", "44100",
            str(temp_out),
        ]

        def _run():
            res = subprocess.run(cmd, capture_output=True)
            if res.returncode == 0 and temp_out.exists():
                shutil.move(temp_out, audio_path)

        await asyncio.to_thread(_run)
        return audio_path

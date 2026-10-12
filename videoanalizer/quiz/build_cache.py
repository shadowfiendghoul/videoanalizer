"""Remotion Webpack bundle caching and reuse manager."""

import contextlib
import hashlib
import json
import logging
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def resolve_node_binary() -> str:
    """Find system node executable, checking standard install paths on Windows."""
    found = shutil.which("node")
    if found:
        return found
    if platform.system() == "Windows":
        known_win_paths = [
            Path("C:/Program Files/nodejs/node.exe"),
            Path("C:/Program Files (x86)/nodejs/node.exe"),
        ]
        for p in known_win_paths:
            if p.exists():
                return str(p)
    return "node"


class RemotionBundleManager:
    """Manages pre-compiling and caching the Remotion React/Webpack bundle.

    Avoids re-compiling the entire Webpack bundle on each render execution,
    dropping startup latency from ~8-15 seconds down to ~0.1 seconds.
    """

    MANIFEST_NAME = ".bundle_manifest.json"

    def __init__(self, remotion_dir: Path | str, out_dir_name: str = "build") -> None:
        self.remotion_dir = Path(remotion_dir).resolve()
        self.bundle_dir = (self.remotion_dir / out_dir_name).resolve()
        self.manifest_path = self.bundle_dir / self.MANIFEST_NAME

    def compute_source_hash(self) -> str:
        """Compute SHA256 digest of Remotion source files and configurations."""
        hasher = hashlib.sha256()

        # Source code files
        src_dir = self.remotion_dir / "src"
        if src_dir.exists():
            for root, _, files in sorted(os.walk(src_dir)):
                for fname in sorted(files):
                    fpath = Path(root) / fname
                    rel_path = fpath.relative_to(self.remotion_dir).as_posix()
                    hasher.update(rel_path.encode("utf-8"))
                    with contextlib.suppress(OSError):
                        hasher.update(fpath.read_bytes())

        # Config files
        config_files = [
            "remotion.config.ts",
            "package.json",
            "tailwind.config.js",
            "tsconfig.json",
        ]
        for cname in config_files:
            cpath = self.remotion_dir / cname
            if cpath.exists():
                hasher.update(cname.encode("utf-8"))
                with contextlib.suppress(OSError):
                    hasher.update(cpath.read_bytes())

        return hasher.hexdigest()

    def is_bundle_ready(self) -> bool:
        """Check whether the pre-built bundle exists, has index.html, and matches source hash."""
        index_html = self.bundle_dir / "index.html"
        if not index_html.exists():
            return False

        if not self.manifest_path.exists():
            return False

        try:
            with open(self.manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            cached_hash = manifest.get("hash")
            if not cached_hash:
                return False
            return cached_hash == self.compute_source_hash()
        except Exception as e:
            logger.debug("Failed to read bundle manifest: %s", e)
            return False

    def build_bundle(self) -> Path:
        """Execute `remotion bundle` to compile Webpack bundle into output directory."""
        self.bundle_dir.mkdir(parents=True, exist_ok=True)
        node_bin = resolve_node_binary()
        cli_js = (
            self.remotion_dir / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
        ).resolve()

        cmd: list[str]
        if cli_js.exists():
            cmd = [
                node_bin,
                str(cli_js),
                "bundle",
                "src/index.ts",
                f"--out-dir={self.bundle_dir}",
                "--bundle-cache",
            ]
        else:
            cmd = [
                "npx",
                "remotion",
                "bundle",
                "src/index.ts",
                f"--out-dir={self.bundle_dir}",
                "--bundle-cache",
            ]

        logger.info("Building Remotion bundle at %s: %s", self.bundle_dir, " ".join(cmd))
        start_t = time.perf_counter()

        proc = subprocess.run(  # noqa: S603
            cmd,
            cwd=str(self.remotion_dir),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )

        if proc.returncode != 0:
            err_msg = proc.stderr or proc.stdout
            logger.error("Remotion bundle build failed (code %s):\n%s", proc.returncode, err_msg)
            raise RuntimeError(f"Remotion bundle compilation failed:\n{err_msg}")

        elapsed = time.perf_counter() - start_t
        current_hash = self.compute_source_hash()

        manifest_data = {
            "hash": current_hash,
            "built_at": time.time(),
            "build_duration_sec": round(elapsed, 2),
            "entry_point": "src/index.ts",
        }
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        logger.info(
            "Remotion bundle successfully built in %.2fs (manifest hash: %s)",
            elapsed,
            current_hash[:8],
        )
        return self.bundle_dir

    def ensure_bundle(self, force: bool = False) -> Path:
        """Ensure bundle exists and is up to date with source files.

        Returns path to bundle directory.
        """
        if not force and self.is_bundle_ready():
            logger.debug("Remotion bundle is up-to-date at %s, skipping build.", self.bundle_dir)
            return self.bundle_dir

        return self.build_bundle()

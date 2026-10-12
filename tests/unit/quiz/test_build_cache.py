"""Unit tests for RemotionBundleManager."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from videoanalizer.quiz.build_cache import RemotionBundleManager, resolve_node_binary


def test_resolve_node_binary() -> None:
    node = resolve_node_binary()
    assert isinstance(node, str)
    assert len(node) > 0


def test_compute_source_hash(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "index.ts").write_text("console.log('test');", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"name": "test"}', encoding="utf-8")

    manager = RemotionBundleManager(tmp_path)
    h1 = manager.compute_source_hash()
    assert isinstance(h1, str)
    assert len(h1) == 64

    # Identical content -> identical hash
    h2 = manager.compute_source_hash()
    assert h1 == h2

    # Modified content -> different hash
    (src_dir / "index.ts").write_text("console.log('modified');", encoding="utf-8")
    h3 = manager.compute_source_hash()
    assert h1 != h3


def test_is_bundle_ready(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "index.ts").write_text("console.log('ready');", encoding="utf-8")

    manager = RemotionBundleManager(tmp_path)
    assert not manager.is_bundle_ready()

    # Create build dir with index.html but no manifest
    manager.bundle_dir.mkdir(parents=True)
    (manager.bundle_dir / "index.html").write_text("<html></html>", encoding="utf-8")
    assert not manager.is_bundle_ready()

    # Create manifest with mismatching hash
    with open(manager.manifest_path, "w", encoding="utf-8") as f:
        json.dump({"hash": "wrong_hash"}, f)
    assert not manager.is_bundle_ready()

    # Create manifest with matching hash
    correct_hash = manager.compute_source_hash()
    with open(manager.manifest_path, "w", encoding="utf-8") as f:
        json.dump({"hash": correct_hash}, f)
    assert manager.is_bundle_ready()


def test_ensure_bundle_skips_when_ready(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "index.ts").write_text("console.log('skip');", encoding="utf-8")

    manager = RemotionBundleManager(tmp_path)
    manager.bundle_dir.mkdir(parents=True)
    (manager.bundle_dir / "index.html").write_text("<html></html>", encoding="utf-8")
    correct_hash = manager.compute_source_hash()
    with open(manager.manifest_path, "w", encoding="utf-8") as f:
        json.dump({"hash": correct_hash}, f)

    with patch.object(manager, "build_bundle") as mock_build:
        out = manager.ensure_bundle(force=False)
        assert out == manager.bundle_dir
        mock_build.assert_not_called()


def test_build_bundle_invokes_cli_and_writes_manifest(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "index.ts").write_text("console.log('build');", encoding="utf-8")

    manager = RemotionBundleManager(tmp_path)

    fake_proc = MagicMock()
    fake_proc.returncode = 0
    fake_proc.stdout = "Bundle created"
    fake_proc.stderr = ""

    with patch("subprocess.run", return_value=fake_proc) as mock_run:
        bundle_path = manager.build_bundle()
        assert bundle_path == manager.bundle_dir
        assert mock_run.called
        assert manager.manifest_path.exists()
        with open(manager.manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest["hash"] == manager.compute_source_hash()

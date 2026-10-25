"""Verify sdist/wheel packaging includes resources and console entry points."""

from __future__ import annotations

import configparser
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory):
    """Build a wheel into a temp dir (requires the ``build`` package)."""
    pytest.importorskip("build")
    out = tmp_path_factory.mktemp("dist")
    # Isolate from any existing project dist/
    cmd = [
        sys.executable,
        "-m",
        "build",
        "--wheel",
        "--outdir",
        str(out),
        str(ROOT),
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"python -m build failed ({proc.returncode}):\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    wheels = sorted(out.glob("handforge-*.whl"))
    assert wheels, f"no wheel produced in {out}"
    return wheels[0]


def test_wheel_contains_resource_pngs(built_wheel: Path):
    with zipfile.ZipFile(built_wheel) as zf:
        names = zf.namelist()
    pngs = [
        n
        for n in names
        if n.startswith("handforge/resources/") and n.endswith(".png")
    ]
    assert pngs, "wheel missing handforge/resources/*.png"
    # Canonical sizes from scripts/generate-app-icons.py
    basenames = {Path(p).name for p in pngs}
    for expected in (
        "app_icon.png",
        "app_icon_16.png",
        "app_icon_32.png",
        "app_icon_64.png",
        "app_icon_128.png",
    ):
        assert expected in basenames, f"missing {expected} in {sorted(basenames)}"


def test_wheel_entry_points(built_wheel: Path):
    with zipfile.ZipFile(built_wheel) as zf:
        ep_name = next(
            n for n in zf.namelist() if n.endswith(".dist-info/entry_points.txt")
        )
        raw = zf.read(ep_name).decode("utf-8")
    parser = configparser.ConfigParser()
    parser.read_string(raw)
    assert parser.has_section("console_scripts")
    scripts = dict(parser.items("console_scripts"))
    assert "handforge" in scripts
    assert "handforge-gui" in scripts
    assert "handforge.cli:main" in scripts["handforge"]
    assert "handforge.app:main" in scripts["handforge-gui"]


def test_package_data_declared_in_pyproject():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "resources/*.png" in text
    assert "resources/fonts/*" in text
    assert 'handforge = "handforge.cli:main"' in text
    assert 'handforge-gui = "handforge.app:main"' in text


def test_source_resources_exist_on_disk():
    res = ROOT / "handforge" / "resources"
    assert res.is_dir()
    pngs = list(res.glob("*.png"))
    assert len(pngs) >= 5
    fonts = list((res / "fonts").glob("Manrope*"))
    assert fonts, "bundled Manrope font missing under handforge/resources/fonts/"

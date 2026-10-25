"""Linux FreeDesktop .desktop launcher install."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from handforge.cli import EXIT_OK, EXIT_USAGE, build_parser, main
from handforge.util import desktop_linux as desk


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
def test_quote_desktop_arg_spaces_and_plain():
    assert desk.quote_desktop_arg("/opt/handforge/bin/handforge-gui") == (
        "/opt/handforge/bin/handforge-gui"
    )
    quoted = desk.quote_desktop_arg("/path with spaces/handforge-gui")
    assert quoted.startswith('"') and quoted.endswith('"')
    assert "spaces" in quoted


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
def test_render_desktop_file_contains_required_keys():
    body = desk.render_desktop_file(
        exec_line="/tmp/fake-handforge-gui",
        try_exec="/tmp/fake-handforge-gui",
    )
    assert "Type=Application" in body
    assert "Name=HandForge" in body
    assert "Exec=/tmp/fake-handforge-gui" in body
    assert "TryExec=/tmp/fake-handforge-gui" in body
    assert f"Icon={desk.ICON_NAME}" in body
    assert "Categories=AudioVideo;AudioVideoEditing;" in body


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
def test_install_and_uninstall_under_prefix(tmp_path, monkeypatch):
    # Point resolve_gui_executable at a fake script under tmp
    bindir = tmp_path / "bin"
    bindir.mkdir()
    gui = bindir / "handforge-gui"
    gui.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    gui.chmod(0o755)
    fake_python = bindir / "python3"
    fake_python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake_python.chmod(0o755)
    monkeypatch.setattr(sys, "executable", str(fake_python))

    prefix = tmp_path / "share"
    result = desk.install_desktop(prefix=prefix, dry_run=False)
    assert result.desktop_path.is_file()
    text = result.desktop_path.read_text(encoding="utf-8")
    assert "Name=HandForge" in text
    assert str(gui) in text
    assert result.icon_paths
    for icon in result.icon_paths:
        assert icon.is_file()
        assert icon.stat().st_size > 0

    ok, msg = desk.validate_desktop_file(result.desktop_path)
    assert ok, msg

    removed = desk.uninstall_desktop(prefix=prefix)
    assert result.desktop_path in removed
    assert not result.desktop_path.exists()
    for icon in result.icon_paths:
        assert not icon.exists()


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
def test_dry_run_writes_nothing(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    gui = bindir / "handforge-gui"
    gui.write_text("#!/bin/sh\n", encoding="utf-8")
    gui.chmod(0o755)
    py = bindir / "python3"
    py.write_text("#!/bin/sh\n", encoding="utf-8")
    py.chmod(0o755)
    monkeypatch.setattr(sys, "executable", str(py))

    prefix = tmp_path / "share"
    result = desk.install_desktop(prefix=prefix, dry_run=True)
    assert result.dry_run is True
    assert not result.desktop_path.exists()
    assert result.exec_line


def test_parser_install_desktop_flags():
    parser = build_parser()
    args = parser.parse_args(["install-desktop", "--dry-run", "--prefix", "/tmp/x"])
    assert args.command == "install-desktop"
    assert args.dry_run is True
    assert args.prefix == "/tmp/x"


@pytest.mark.skipif(sys.platform.startswith("linux"), reason="non-Linux guard")
def test_main_install_desktop_rejects_non_linux():
    code = main(["install-desktop"])
    assert code == EXIT_USAGE


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
def test_main_install_desktop_dry_run(tmp_path, monkeypatch, capsys):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    gui = bindir / "handforge-gui"
    gui.write_text("#!/bin/sh\n", encoding="utf-8")
    gui.chmod(0o755)
    py = bindir / "python3"
    py.write_text("#!/bin/sh\n", encoding="utf-8")
    py.chmod(0o755)
    monkeypatch.setattr(sys, "executable", str(py))

    prefix = tmp_path / "xdg-share"
    code = main(["install-desktop", "--dry-run", "--prefix", str(prefix)])
    assert code == EXIT_OK
    out = capsys.readouterr().out
    assert "Would write desktop entry" in out
    assert not (prefix / "applications" / desk.DESKTOP_FILENAME).exists()


def test_packaging_template_exists():
    path = desk.packaging_template_path()
    # Present in the git checkout; may be absent from a bare wheel extract.
    if not path.is_file():
        pytest.skip("packaging/linux/handforge.desktop not in this tree")
    text = path.read_text(encoding="utf-8")
    assert "[Desktop Entry]" in text
    assert "Name=HandForge" in text
    assert "@HANDFORGE_GUI@" in text


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
def test_resolve_gui_prefers_venv_sibling_not_symlink_target(tmp_path, monkeypatch):
    """Venv python is often a symlink to /usr/bin/python*; keep looking in .venv/bin."""
    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    real_py = tmp_path / "real-python"
    real_py.write_text("#!/bin/sh\n", encoding="utf-8")
    real_py.chmod(0o755)
    venv_py = venv_bin / "python"
    venv_py.symlink_to(real_py)
    gui = venv_bin / "handforge-gui"
    gui.write_text("#!/bin/sh\n", encoding="utf-8")
    gui.chmod(0o755)
    monkeypatch.setattr(sys, "executable", str(venv_py))

    exec_line, try_exec = desk.resolve_gui_executable()
    assert "handforge-gui" in try_exec
    assert str(venv_bin) in try_exec
    assert "/usr/bin" not in try_exec
    assert "handforge-gui" in exec_line

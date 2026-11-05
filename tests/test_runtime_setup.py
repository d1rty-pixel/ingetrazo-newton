import json
import stat
import sys
from pathlib import Path

import pytest

from newton import runtime_setup as rs


@pytest.fixture
def root(tmp_path):
    return tmp_path / "newton-runtime"


def fake_uv(directory, fail=False):
    """A uv stand-in: `venv` makes a fake venv, `pip` does nothing."""
    path = directory / "uv"
    interpreter = "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    path.write_text(f"""#!{sys.executable}
import sys, pathlib
args = sys.argv[1:]
if {fail!r}:
    print("boom"); sys.exit(3)
if args[0] == "venv":
    target = pathlib.Path(args[-1]) / "{interpreter}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("")
""")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


def test_runtime_dir_is_next_to_plugins_folder(tmp_path):
    assert rs.runtime_dir(tmp_path) == tmp_path / "newton-runtime"
    assert rs.runtime_dir().name in ("newton-runtime", ".newton-runtime")


def test_flatpak_data_dir():
    assert rs.flatpak_data_dir().parts[-5:] == (".var", "app", "com.ingetrazo.IngeTrazo", "data", "ingetrazo")


def test_resolve_prefers_runtime_json(root, tmp_path):
    python = tmp_path / "py"
    python.write_text("")
    root.mkdir()
    (root / "runtime.json").write_text(json.dumps({"python": str(python)}))
    assert rs.resolve(root) == str(python)


def test_resolve_ignores_stale_config_and_falls_back_to_venv(root):
    root.mkdir()
    (root / "runtime.json").write_text(json.dumps({"python": "/nonexistent/python"}))
    assert rs.resolve(root) in ("", str(Path(rs.__file__).parent.parent / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")))
    rs.venv_python(root).parent.mkdir(parents=True)
    rs.venv_python(root).write_text("")
    assert rs.resolve(root) == str(rs.venv_python(root))


@pytest.mark.parametrize("windows, relative", [(False, "bin/python"), (True, "Scripts/python.exe")])
def test_resolve_finds_checkout_venv_for_each_platform(root, tmp_path, monkeypatch, windows, relative):
    package = tmp_path / "checkout" / "newton"
    package.mkdir(parents=True)
    python = tmp_path / "checkout" / ".venv" / relative
    python.parent.mkdir(parents=True)
    python.write_text("")
    monkeypatch.setattr(rs, "__file__", str(package / "runtime_setup.py"))
    monkeypatch.setattr(rs, "_windows", lambda: windows)
    assert rs.resolve(root) == str(python)


def test_check_rejects_missing_interpreter():
    ok, message = rs.check("/nonexistent/python")
    assert not ok and "does not exist" in message


def test_check_reports_missing_mujoco(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "_PROBE", "import definitely_not_installed_module")
    ok, message = rs.check(sys.executable)
    assert not ok and "MuJoCo is not usable" in message


def test_check_rejects_wrong_mujoco_version(monkeypatch):
    monkeypatch.setattr(rs, "_PROBE", "print('3.12', '0.0.1')")
    ok, message = rs.check(sys.executable)
    assert not ok and "0.0.1" in message


def test_check_accepts_pinned_version(monkeypatch):
    monkeypatch.setattr(rs, "_PROBE", f"print('3.12', '{rs.MUJOCO_VERSION}')")
    assert rs.check(sys.executable)[0]


def test_clean_env_restores_original_library_path():
    env = rs.clean_env({"LD_LIBRARY_PATH": "/bundle", "LD_LIBRARY_PATH_ORIG": "/system", "HOME": "/h"})
    assert env["LD_LIBRARY_PATH"] == "/system" and "LD_LIBRARY_PATH_ORIG" not in env and env["HOME"] == "/h"


def test_install_with_fake_uv_writes_config_and_is_idempotent(root, tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "check", lambda python: (True, "ok"))
    events = []
    uv = fake_uv(tmp_path)
    python = rs.install(root, events.append, uv=uv)
    assert python == str(rs.venv_python(root))
    assert json.loads((root / "runtime.json").read_text())["python"] == python
    assert (root / rs.MARKER).is_file()
    assert [e["step"] for e in events][-1] == "done"
    assert rs.install(root, uv=uv) == python


def test_install_failure_leaves_no_config(root, tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "check", lambda python: (True, "ok"))
    with pytest.raises(rs.SetupError, match="boom"):
        rs.install(root, uv=fake_uv(tmp_path, fail=True))
    assert not (root / "runtime.json").exists()


def test_install_refuses_foreign_folder(root, tmp_path):
    root.mkdir()
    (root / "something").write_text("")
    with pytest.raises(rs.SetupError, match="not a Newton runtime"):
        rs.install(root, uv=fake_uv(tmp_path))


def test_install_cancel(root, tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "check", lambda python: (True, "ok"))
    with pytest.raises(rs.SetupError, match="Cancelled"):
        rs.install(root, uv=fake_uv(tmp_path), cancel=lambda: True)


def test_switch_disables_install_and_download(root, tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "RUNTIME_SETUP_ENABLED", False)
    with pytest.raises(rs.SetupError, match="disabled"):
        rs.install(root, uv=fake_uv(tmp_path))
    monkeypatch.setattr(rs, "RUNTIME_SETUP_ENABLED", True)
    monkeypatch.setattr(rs.shutil, "which", lambda name: None)
    with pytest.raises(rs.SetupError, match="downloading it is disabled"):
        rs.install(root, allow_download=False)


def test_download_rejects_wrong_hash(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        chunks = [b"abc", b""]
        def read(self, size): return self.chunks.pop(0)
    monkeypatch.setattr(rs.urllib.request, "urlopen", lambda *a, **k: Response())
    with pytest.raises(rs.SetupError, match="SHA-256"):
        rs._download("https://example.invalid/uv", "0" * 64, lambda: False)


def test_pinned_downloads_are_https_with_full_hashes():
    for name, sha256, member in rs.UV_ARCHIVES.values():
        assert len(sha256) == 64 and int(sha256, 16) >= 0
    assert rs.UV_URL.startswith("https://")


def test_uninstall_requires_marker(root):
    root.mkdir()
    (root / "keep").write_text("")
    with pytest.raises(rs.SetupError):
        rs.uninstall(root)
    (root / rs.MARKER).write_text("")
    rs.uninstall(root)
    assert not root.exists()


def test_command_line(root, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(rs, "check", lambda python: (True, "ok"))
    data = tmp_path / "data"
    assert rs.main(["install", "--data-dir", str(data), "--yes", "--uv", fake_uv(tmp_path), "--json"]) == rs.OK
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert lines[-1]["step"] == "done"
    assert rs.main(["path", "--data-dir", str(data)]) == rs.OK
    assert rs.main(["uninstall", "--data-dir", str(data), "--yes"]) == rs.OK
    assert rs.main(["path", "--data-dir", str(data)]) in (rs.OK, rs.FAILED)
    assert rs.main(["install", "--flatpak", "--data-dir", "x"]) == rs.USAGE
    assert rs.main(["bogus"]) == rs.USAGE


def test_requirements_pin_mujoco():
    assert f"mujoco=={rs.MUJOCO_VERSION}" in rs.REQUIREMENTS.read_text()


def test_uninstall_refuses_a_symlinked_folder_and_keeps_the_target(root, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep").write_text("")
    (outside / rs.MARKER).write_text("")
    root.parent.mkdir(parents=True, exist_ok=True)
    root.symlink_to(outside, target_is_directory=True)
    with pytest.raises(rs.SetupError):
        rs.uninstall(root)
    assert (outside / "keep").exists() and not rs.is_managed(root)


def test_uninstall_removes_links_inside_without_following_them(root, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep").write_text("")
    root.mkdir()
    (root / rs.MARKER).write_text("")
    (root / "link").symlink_to(outside, target_is_directory=True)
    rs.uninstall(root)
    assert not root.exists() and (outside / "keep").exists()

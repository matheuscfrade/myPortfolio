from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_packaged_app_declares_pillow_dependency():
    requirements = (ROOT / "requirements.txt").read_text("utf-8").splitlines()

    assert "Pillow" in requirements


def test_pyinstaller_collects_complete_pil_package():
    spec = (ROOT / "packaging" / "portfolio-admin.spec").read_text("utf-8")

    assert "collect_submodules(\"PIL\")" in spec
    assert "\"PIL\"" in spec


def test_windows_build_script_resolves_python_executable():
    script = (ROOT / "packaging" / "build_windows.ps1").read_text("utf-8")

    assert "$PythonExe" in script
    assert "Get-Command python" in script
    assert "$LASTEXITCODE" in script
    assert "--workpath" in script
    assert ".codex_tmp" in script


def test_installer_version_matches_next_release():
    installer = (ROOT / "packaging" / "installer.iss").read_text("utf-8")

    assert '#define MyAppVersion "1.0.5"' in installer


if __name__ == "__main__":
    test_packaged_app_declares_pillow_dependency()
    test_pyinstaller_collects_complete_pil_package()
    test_windows_build_script_resolves_python_executable()
    test_installer_version_matches_next_release()

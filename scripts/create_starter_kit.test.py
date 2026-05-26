import importlib.util
import zipfile
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "create_starter_kit.py"
spec = importlib.util.spec_from_file_location("create_starter_kit", MODULE_PATH)
create_starter_kit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(create_starter_kit)


def test_should_include_scripts_on_windows_style_paths():
    root = create_starter_kit.ROOT
    assert create_starter_kit.should_include(root / "scripts" / "servidor_admin.py")
    assert create_starter_kit.should_include(root / "scripts" / "gerar_dados.py")


def test_zip_contains_required_runtime_files():
    output = create_starter_kit.ROOT / ".codex_tmp" / "starter-test.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    original_output = create_starter_kit.OUTPUT_ZIP
    create_starter_kit.OUTPUT_ZIP = output
    try:
        create_starter_kit.main()
    finally:
        create_starter_kit.OUTPUT_ZIP = original_output

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())

    assert "scripts/servidor_admin.py" in names
    assert "scripts/gerar_dados.py" in names
    assert "scripts/app_runtime.py" in names
    assert "scripts/create_public_package.py" in names
    assert "Gerar_Pasta_Publica.bat" in names
    assert not any(name.startswith("Documentos/") for name in names)
    assert "site/dados.js" not in names


if __name__ == "__main__":
    test_should_include_scripts_on_windows_style_paths()
    test_zip_contains_required_runtime_files()

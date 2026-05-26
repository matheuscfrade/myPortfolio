import json
import os
import shutil
from pathlib import Path

import app_runtime


class EnvPatch:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.previous = None

    def __enter__(self):
        self.previous = os.environ.get(self.key)
        os.environ[self.key] = self.value

    def __exit__(self, exc_type, exc, tb):
        if self.previous is None:
            os.environ.pop(self.key, None)
        else:
            os.environ[self.key] = self.previous


def make_workspace_tmp(name: str) -> Path:
    workspace = Path(__file__).resolve().parents[1]
    base = (workspace / ".codex_tmp" / name).resolve()
    if workspace.resolve() not in base.parents:
        raise RuntimeError(f"Unsafe temporary path: {base}")
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    return base


def test_runtime_uses_explicit_data_dir_and_creates_defaults():
    data_dir = make_workspace_tmp("runtime-defaults") / "data"
    with EnvPatch("PORTFOLIO_DATA_DIR", str(data_dir)):
        runtime = app_runtime.get_runtime()
        app_runtime.ensure_data_layout(runtime)

    assert runtime.data_dir == data_dir.resolve()
    assert (data_dir / "Documentos").is_dir()
    assert json.loads((data_dir / "site" / "edicoes.json").read_text("utf-8")) == {}
    assert json.loads((data_dir / "site" / "ocultos.json").read_text("utf-8")) == []
    assert json.loads((data_dir / "site" / "categorias.json").read_text("utf-8")) == []
    assert "const DOCUMENTOS = [];" in (data_dir / "site" / "dados.js").read_text("utf-8")
    config = json.loads((data_dir / "config" / "app.json").read_text("utf-8"))
    assert config["displayName"] == "Seu Nome"


def test_config_roundtrip():
    data_dir = make_workspace_tmp("runtime-config")
    with EnvPatch("PORTFOLIO_DATA_DIR", str(data_dir)):
        runtime = app_runtime.get_runtime()
        app_runtime.ensure_data_layout(runtime)

        config = app_runtime.load_app_config(runtime)
        config["displayName"] = "Ana Silva"
        config["subtitle"] = "Arquivo Profissional"
        app_runtime.save_app_config(runtime, config)

        loaded = app_runtime.load_app_config(runtime)
        assert loaded["displayName"] == "Ana Silva"
        assert loaded["subtitle"] == "Arquivo Profissional"
        assert loaded["portfolioTitle"] == "Portfolio Documental"


def test_empty_install_generates_empty_dados():
    data_dir = make_workspace_tmp("runtime-empty-install")
    with EnvPatch("PORTFOLIO_DATA_DIR", str(data_dir)):
        runtime = app_runtime.get_runtime()
        app_runtime.ensure_data_layout(runtime)

        import gerar_dados

        records = gerar_dados.catalog_folder(runtime.documentos_dir)
        gerar_dados.generate_js(records, runtime.site_dir / "dados.js")

        text = (runtime.site_dir / "dados.js").read_text("utf-8")
        assert "const DOCUMENTOS = [];" in text


if __name__ == "__main__":
    test_runtime_uses_explicit_data_dir_and_creates_defaults()
    test_config_roundtrip()
    test_empty_install_generates_empty_dados()

import importlib.util
import json
import shutil
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "create_public_package.py"
spec = importlib.util.spec_from_file_location("create_public_package", MODULE_PATH)
create_public_package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(create_public_package)


def make_workspace_tmp(name: str) -> Path:
    workspace = Path(__file__).resolve().parents[1]
    base = (workspace / ".codex_tmp" / name).resolve()
    if workspace.resolve() not in base.parents:
        raise RuntimeError(f"Unsafe temporary path: {base}")
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    return base


def test_public_package_excludes_admin_and_hidden_docs():
    tmp = make_workspace_tmp("public-package")
    root = tmp / "root"
    public = root / "site-publico"
    site = root / "site"
    docs = root / "Documentos"
    config = root / "config"

    public.mkdir(parents=True)
    site.mkdir(parents=True)
    config.mkdir(parents=True)
    (docs / "Comissao" / "2026").mkdir(parents=True)
    (docs / "Outro" / "2026").mkdir(parents=True)

    (public / "index.html").write_text("<html></html>", "utf-8")
    (public / "main.js").write_text("console.log('ok')", "utf-8")
    (public / "styles.css").write_text("body{}", "utf-8")
    (docs / "Comissao" / "2026" / "a.pdf").write_bytes(b"a")
    (docs / "Outro" / "2026" / "b.pdf").write_bytes(b"b")
    (site / "dados.js").write_text("const DOCUMENTOS = [];", "utf-8")
    (site / "edicoes.json").write_text("{}", "utf-8")
    (site / "ocultos.json").write_text(json.dumps(["Outro/2026/b.pdf"]), "utf-8")
    (site / "categorias.json").write_text("[]", "utf-8")
    (config / "app.json").write_text(json.dumps({"displayName": "Ana"}), "utf-8")

    out = tmp / "out"
    create_public_package.create_public_package(root, out)

    assert (out / "index.html").exists()
    assert (out / "main.js").exists()
    assert (out / "shared-data" / "dados.js").exists()
    assert (out / "shared-data" / "config.json").exists()
    assert (out / "Documentos" / "Comissao" / "2026" / "a.pdf").exists()
    assert not (out / "Documentos" / "Outro" / "2026" / "b.pdf").exists()
    assert not (out / "admin").exists()


if __name__ == "__main__":
    test_public_package_excludes_admin_and_hidden_docs()

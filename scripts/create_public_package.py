import json
import os
import shutil
import stat
import time
from pathlib import Path


SHARED_FILES = ("dados.js", "edicoes.json", "ocultos.json", "categorias.json")
SKIPPED_PUBLIC_FILES = {"README.md"}


def handle_remove_error(function, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        function(path)
    except Exception:
        raise exc_info[1]


def remove_tree(path: Path) -> None:
    if not path.exists():
        return
    for attempt in range(3):
        try:
            shutil.rmtree(path, onerror=handle_remove_error)
            return
        except PermissionError:
            if attempt == 2:
                raise
            time.sleep(0.4)


def read_hidden_documents(site_dir: Path) -> set[str]:
    ocultos_file = site_dir / "ocultos.json"
    if not ocultos_file.exists():
        return set()
    try:
        data = json.loads(ocultos_file.read_text("utf-8"))
    except Exception:
        return set()
    if not isinstance(data, list):
        return set()
    return {str(item).replace("\\", "/") for item in data}


def copy_tree_contents(source: Path, destination: Path) -> None:
    if not source.exists():
        return
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if item.name in SKIPPED_PUBLIC_FILES:
            continue
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def copy_public_documents(documentos_dir: Path, output_dir: Path, hidden: set[str]) -> None:
    if not documentos_dir.exists():
        return
    for pdf_path in documentos_dir.rglob("*.pdf"):
        rel = pdf_path.relative_to(documentos_dir).as_posix()
        if rel in hidden:
            continue
        target = output_dir / "Documentos" / Path(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, target)


def create_public_package(root: Path | str, output_dir: Path | str, public_site_dir: Path | str | None = None) -> Path:
    root = Path(root)
    output_dir = Path(output_dir)
    public_site = Path(public_site_dir) if public_site_dir else root / "site-publico"
    site_dir = root / "site"
    config_file = root / "config" / "app.json"

    if output_dir.exists():
        remove_tree(output_dir)
    output_dir.mkdir(parents=True)

    copy_tree_contents(public_site, output_dir)

    shared_dir = output_dir / "shared-data"
    shared_dir.mkdir(parents=True, exist_ok=True)
    for filename in SHARED_FILES:
        source = site_dir / filename
        if source.exists():
            shutil.copy2(source, shared_dir / filename)

    if config_file.exists():
        shutil.copy2(config_file, shared_dir / "config.json")

    hidden = read_hidden_documents(site_dir)
    copy_public_documents(root / "Documentos", output_dir, hidden)
    return output_dir


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    output = project_root / "dist-publico"
    create_public_package(project_root, output)
    print(f"[OK] Pacote publico criado em: {output}")

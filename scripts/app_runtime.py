import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path


APP_DIR_NAME = "Portfolio Profissional"


@dataclass(frozen=True)
class RuntimePaths:
    resource_dir: Path
    data_dir: Path
    site_dir: Path
    documentos_dir: Path
    public_site_dir: Path
    admin_site_dir: Path
    scripts_dir: Path
    config_dir: Path
    config_file: Path


DEFAULT_CONFIG = {
    "displayName": "Seu Nome",
    "subtitle": "Portfolio Profissional",
    "portfolioTitle": "Portfolio Documental",
    "organization": "",
}


def get_resource_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)).resolve()
    return Path(__file__).resolve().parents[1]


def get_default_data_dir(resource_dir: Path) -> Path:
    explicit = os.environ.get("PORTFOLIO_DATA_DIR")
    if explicit:
        return Path(explicit).expanduser().resolve()

    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return (Path(base) / APP_DIR_NAME).resolve()

    return resource_dir.resolve()


def get_runtime() -> RuntimePaths:
    resource_dir = get_resource_dir()
    data_dir = get_default_data_dir(resource_dir)
    return RuntimePaths(
        resource_dir=resource_dir,
        data_dir=data_dir,
        site_dir=data_dir / "site",
        documentos_dir=data_dir / "Documentos",
        public_site_dir=resource_dir / "site-publico",
        admin_site_dir=resource_dir / "admin",
        scripts_dir=resource_dir / "scripts",
        config_dir=data_dir / "config",
        config_file=data_dir / "config" / "app.json",
    )


def ensure_json_file(path: Path, default_value) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(default_value, ensure_ascii=False, indent=2), "utf-8")


def ensure_dados_file(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "// Gerado automaticamente por gerar_dados.py\n"
        "// Fonte: Documentos/\n"
        "// Total: 0 documentos\n\n"
        'const BASE_URL = "../Documentos/";\n'
        'const ADMIN_HASH = "";\n'
        "const DOCUMENTOS = [];\n",
        "utf-8",
    )


def normalize_app_config(config: dict | None) -> dict:
    merged = dict(DEFAULT_CONFIG)
    if isinstance(config, dict):
        for key in DEFAULT_CONFIG:
            value = config.get(key)
            if value is not None:
                merged[key] = str(value).strip()
    if not merged["displayName"]:
        merged["displayName"] = DEFAULT_CONFIG["displayName"]
    return merged


def ensure_data_layout(runtime: RuntimePaths | None = None) -> RuntimePaths:
    runtime = runtime or get_runtime()
    runtime.documentos_dir.mkdir(parents=True, exist_ok=True)
    runtime.site_dir.mkdir(parents=True, exist_ok=True)
    runtime.config_dir.mkdir(parents=True, exist_ok=True)

    ensure_dados_file(runtime.site_dir / "dados.js")
    ensure_json_file(runtime.site_dir / "edicoes.json", {})
    ensure_json_file(runtime.site_dir / "ocultos.json", [])
    ensure_json_file(runtime.site_dir / "categorias.json", [])
    ensure_json_file(runtime.config_file, DEFAULT_CONFIG)
    return runtime


def load_app_config(runtime: RuntimePaths | None = None) -> dict:
    runtime = runtime or get_runtime()
    ensure_data_layout(runtime)
    try:
        data = json.loads(runtime.config_file.read_text("utf-8"))
    except Exception:
        data = {}
    config = normalize_app_config(data)
    if config != data:
        save_app_config(runtime, config)
    return config


def save_app_config(runtime: RuntimePaths | None, config: dict) -> dict:
    runtime = runtime or get_runtime()
    runtime.config_dir.mkdir(parents=True, exist_ok=True)
    normalized = normalize_app_config(config)
    runtime.config_file.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        "utf-8",
    )
    return normalized

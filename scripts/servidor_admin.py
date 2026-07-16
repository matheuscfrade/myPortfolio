import json
import os
import re
import shutil
import sys
import threading
import webbrowser
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

from flask import Flask, jsonify, redirect, request, send_file, send_from_directory

from app_runtime import ensure_data_layout, get_runtime, load_app_config


RUNTIME = get_runtime()
ensure_data_layout(RUNTIME)

SITE_DIR = RUNTIME.site_dir
EXPORT_DIR = RUNTIME.documentos_dir
PUBLIC_SITE_DIR = RUNTIME.public_site_dir
ADMIN_SITE_DIR = RUNTIME.admin_site_dir
CATEGORIES_FILE = SITE_DIR / "categorias.json"
RECOVERY_FOLDER = "_Excluidos"

app = Flask(__name__, static_folder=None)


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception:
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def load_categories():
    data = read_json(CATEGORIES_FILE, [])
    return data if isinstance(data, list) else []


def save_categories(categories):
    write_json(CATEGORIES_FILE, categories)


def safe_filename(value):
    return re.sub(r'[\\/*?:"<>|]', "", str(value or "")).strip()


# Windows traditional MAX_PATH is 260. Stay under it so shutil/move works without long-path
# opt-in. Subject text belongs in metadata (edicoes.json / PDF), not in unbounded filenames.
MAX_WINDOWS_PATH = 240
MAX_PDF_FILENAME = 120


def normalize_categoria_folder(categoria: str) -> str:
    cat = safe_filename(categoria)
    if cat in ("Cargo/Função", "CargoFunção", "Cargo - Função", "Cargofunção"):
        return "Cargo-Função"
    return cat or "Não Categorizado"


def build_pdf_filename(nome: str, assunto: str = "", *, max_filename: int = MAX_PDF_FILENAME) -> str:
    """Build a filesystem-safe PDF name that fits Windows path limits.

    Short subjects may still be appended as a hint; long subjects are omitted from the
    filename (they remain in edicoes.json and PDF metadata).
    """
    max_filename = max(24, int(max_filename))
    # reserve for ".pdf"
    max_stem = max(20, max_filename - 4)

    base = safe_filename(nome) or "documento"
    subject = safe_filename(assunto)

    if subject:
        combined = f"{base} - {subject}"
        # Only keep the subject fragment when the full stem stays reasonably short.
        if len(combined) <= max_stem and len(subject) <= 60:
            stem = combined
        else:
            stem = base
    else:
        stem = base

    if len(stem) > max_stem:
        stem = stem[:max_stem].rstrip(" .-_")
    if not stem:
        stem = "documento"
    return f"{stem}.pdf"


def build_document_target(categoria: str, ano: str, nome: str, assunto: str = "") -> Path:
    """Destination path for a document under Documentos/<categoria>/<ano>/."""
    folder = EXPORT_DIR / normalize_categoria_folder(categoria) / safe_filename(str(ano))
    # Cap filename so the absolute path stays under MAX_WINDOWS_PATH.
    # len(folder) + 1 (separator) + filename <= MAX_WINDOWS_PATH
    room_for_name = MAX_WINDOWS_PATH - len(str(folder.resolve() if folder.exists() else folder)) - 1
    room_for_name = max(24, min(MAX_PDF_FILENAME, room_for_name))
    return folder / build_pdf_filename(nome, assunto, max_filename=room_for_name)


def resolve_document_file(arquivo: str) -> tuple[str, Path]:
    if not isinstance(arquivo, str):
        raise ValueError("Arquivo inválido.")

    normalized = arquivo.replace("\\", "/").strip()
    if (
        not normalized
        or normalized.startswith("/")
        or re.match(r"^[A-Za-z]:", normalized)
        or normalized.split("/")[0] == RECOVERY_FOLDER
    ):
        raise ValueError("Caminho de arquivo inválido.")

    candidate = (EXPORT_DIR / normalized).resolve()
    root = EXPORT_DIR.resolve()
    if root != candidate and root not in candidate.parents:
        raise ValueError("Caminho de arquivo inválido.")
    if not candidate.is_file():
        raise FileNotFoundError("Arquivo não encontrado.")
    return normalized, candidate


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 1
    while True:
        candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def cleanup_document_metadata(old_key: str, new_key: str | None = None, edit_payload: dict | None = None) -> None:
    edicoes_file = SITE_DIR / "edicoes.json"
    edicoes = read_json(edicoes_file, {})
    if not isinstance(edicoes, dict):
        edicoes = {}

    if old_key in edicoes and old_key != new_key:
        del edicoes[old_key]
    if new_key and edit_payload is not None:
        edicoes[new_key] = edit_payload
    write_json(edicoes_file, edicoes)

    ocultos_file = SITE_DIR / "ocultos.json"
    ocultos = read_json(ocultos_file, [])
    if not isinstance(ocultos, list):
        ocultos = []
    ocultos = [item for item in ocultos if item != old_key]
    if new_key and old_key in read_json(ocultos_file, []):
        ocultos.append(new_key)
    write_json(ocultos_file, ocultos)


def sync_data() -> None:
    from gerar_dados import main as gerar_dados_main

    gerar_dados_main()


def create_public_package_for_runtime() -> Path:
    from create_public_package import create_public_package

    output = RUNTIME.data_dir / "dist-publico"
    return create_public_package(RUNTIME.data_dir, output, public_site_dir=PUBLIC_SITE_DIR)


def count_catalogable_pdfs() -> int:
    count = 0
    for pdf_path in EXPORT_DIR.rglob("*.pdf"):
        try:
            rel = pdf_path.relative_to(EXPORT_DIR)
        except ValueError:
            continue
        if rel.parts and rel.parts[0] == RECOVERY_FOLDER:
            continue
        count += 1
    return count


def dados_file_is_empty() -> bool:
    dados_file = SITE_DIR / "dados.js"
    if not dados_file.exists():
        return True
    try:
        text = dados_file.read_text("utf-8")
    except OSError:
        return False
    return "const DOCUMENTOS = [];" in text


def ensure_initial_catalog() -> None:
    if count_catalogable_pdfs() == 0 or not dados_file_is_empty():
        return
    try:
        print("[INFO] Documentos encontrados com dados.js vazio. Sincronizando automaticamente...")
        sync_data()
    except Exception as error:
        print(f"[AVISO] Sincronização automática inicial falhou: {error}")


def update_pdf_metadata(file_path, novo_nome, novo_assunto):
    try:
        from pypdf import PdfReader, PdfWriter

        reader = PdfReader(str(file_path))
        if reader.is_encrypted:
            return False

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        metadata = reader.metadata
        new_meta = {}
        if metadata:
            new_meta.update(metadata)
        new_meta.update({"/Title": novo_nome, "/Subject": novo_assunto})
        writer.add_metadata(new_meta)

        temp_path = file_path.with_suffix(".tmp.pdf")
        with open(temp_path, "wb") as file:
            writer.write(file)
        shutil.move(temp_path, file_path)
        return True
    except Exception as error:
        print(f"[AVISO] Não foi possível atualizar metadados do PDF {file_path.name}: {error}")
        return False


@app.route("/")
def index():
    return redirect("/admin/")


@app.route("/Documentos/<path:filename>")
def serve_documentos(filename):
    return send_from_directory(EXPORT_DIR, filename)


@app.route("/admin/")
@app.route("/admin/<path:filename>")
def serve_admin_site(filename=None):
    return send_from_directory(ADMIN_SITE_DIR, filename or "index.html")


@app.route("/portfolio/")
@app.route("/portfolio/<path:filename>")
def serve_public_site(filename=None):
    return redirect("/admin/")


@app.route("/shared-data/dados.js")
def serve_shared_dados():
    return send_from_directory(SITE_DIR, "dados.js")


@app.route("/shared-data/config.json")
def serve_shared_config():
    return jsonify(load_app_config(RUNTIME))


@app.route("/shared-data/<path:filename>")
def serve_shared_data(filename):
    if filename not in ("edicoes.json", "ocultos.json", "categorias.json"):
        return "Forbidden", 403
    return send_from_directory(SITE_DIR, filename)


@app.route("/api/config", methods=["GET"])
def app_config():
    return jsonify(load_app_config(RUNTIME))


@app.route("/api/runtime-status", methods=["GET"])
def runtime_status():
    return jsonify({
        "data_dir": str(RUNTIME.data_dir),
        "documentos_dir": str(EXPORT_DIR),
        "site_dir": str(SITE_DIR),
        "dados_js": str(SITE_DIR / "dados.js"),
        "pdf_count": count_catalogable_pdfs(),
    })


@app.route("/api/abrir-documentos", methods=["POST"])
def abrir_documentos():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        return jsonify({"error": "Abertura de pasta disponivel apenas no Windows."}), 400
    os.startfile(str(EXPORT_DIR))
    return jsonify({"success": True})


@app.route("/api/categorias", methods=["GET", "POST"])
def categorias():
    if request.method == "GET":
        return jsonify(load_categories())

    data = request.get_json() or {}
    nome = re.sub(r"\s+", " ", data.get("nome", "")).strip()
    color = data.get("color", "#546E7A").strip() or "#546E7A"
    if not nome:
        return jsonify({"error": "Informe o nome da categoria."}), 400
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        return jsonify({"error": "Cor inválida."}), 400

    categories = load_categories()
    if any((item.get("nome", "") or "").lower() == nome.lower() for item in categories if isinstance(item, dict)):
        return jsonify({"error": "Essa categoria já existe."}), 409

    categories.append({"nome": nome, "color": color})
    categories.sort(key=lambda item: item.get("nome", "").lower())
    save_categories(categories)
    return jsonify(categories)


@app.route("/api/ocultar", methods=["POST"])
def ocultar():
    data = request.json
    if not data or "arquivo" not in data:
        return jsonify({"error": "Dados inválidos."}), 400

    arquivo = data["arquivo"]
    estado_oculto = data.get("oculto", True)
    ocultos_file = SITE_DIR / "ocultos.json"
    ocultos = read_json(ocultos_file, [])
    if not isinstance(ocultos, list):
        ocultos = []

    if estado_oculto and arquivo not in ocultos:
        ocultos.append(arquivo)
    if not estado_oculto and arquivo in ocultos:
        ocultos.remove(arquivo)

    write_json(ocultos_file, ocultos)
    return jsonify({"success": True})


@app.route("/api/sync", methods=["POST"])
def sync_db():
    try:
        print("[INFO] Sincronização manual iniciada.")
        sync_data()
        return jsonify({"success": True})
    except Exception as error:
        print(f"[ERRO] Falha inesperada ao sincronizar: {error}")
        return jsonify({"error": str(error)}), 500


@app.route("/api/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "Nenhum arquivo enviado."}), 400

    nome = request.form.get("nome", "").strip()
    assunto = request.form.get("assunto", "").strip()
    categoria = request.form.get("categoria", "").strip() or "Não Categorizado"
    ano = request.form.get("ano", "").strip()
    data = request.form.get("data", "").strip() or f"{ano}-01-01"
    numero = request.form.get("numero", "").strip()

    if not nome or not ano or not categoria:
        return jsonify({"error": "Dados obrigatórios ausentes."}), 400

    arquivo_alvo = build_document_target(categoria, ano, nome, assunto)
    arquivo_alvo.parent.mkdir(parents=True, exist_ok=True)
    arquivo_novo = unique_path(arquivo_alvo)
    file.save(arquivo_novo)
    update_pdf_metadata(arquivo_novo, nome, assunto)

    novo_arquivo_relativo = arquivo_novo.relative_to(EXPORT_DIR).as_posix()
    cleanup_document_metadata(
        novo_arquivo_relativo,
        novo_arquivo_relativo,
        {
            "nome": nome,
            "assunto": assunto,
            "numero": numero,
            "data": data,
            "categoria": categoria,
        },
    )
    return jsonify({"success": True, "novo_arquivo": novo_arquivo_relativo})


@app.route("/api/editar", methods=["POST"])
def editar():
    data = request.json
    if not data or "arquivo" not in data:
        return jsonify({"error": "Dados inválidos."}), 400

    try:
        arquivo_relativo, arquivo_antigo = resolve_document_file(data["arquivo"])
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 404

    nome = data.get("nome", "").strip()
    assunto = data.get("assunto", "").strip()
    categoria = data.get("categoria", "").strip() or "Não Categorizado"
    data_str = data.get("data", "").strip()
    ano = data_str.split("-")[0] if re.match(r"^\d{4}-\d{2}-\d{2}$", data_str) else ""
    if not ano and str(data.get("ano", "")).isdigit():
        ano = str(data.get("ano"))
    if not ano:
        ano = str(datetime.now().year)

    if not nome:
        return jsonify({"error": "O campo Nome é obrigatório."}), 400

    arquivo_alvo = build_document_target(categoria, ano, nome, assunto)
    arquivo_alvo.parent.mkdir(parents=True, exist_ok=True)
    # Keep the same path when the computed target matches the current file (case-insensitive on Windows).
    if arquivo_antigo.resolve() == arquivo_alvo.resolve():
        arquivo_novo = arquivo_antigo
    else:
        arquivo_novo = unique_path(arquivo_alvo)

    try:
        if arquivo_antigo.resolve() != arquivo_novo.resolve():
            shutil.move(str(arquivo_antigo), str(arquivo_novo))
        update_pdf_metadata(arquivo_novo, nome, assunto)

        chave_nova = arquivo_novo.relative_to(EXPORT_DIR).as_posix()
        cleanup_document_metadata(
            arquivo_relativo,
            chave_nova,
            {
                "nome": nome,
                "assunto": assunto,
                "numero": data.get("numero", "").strip(),
                "data": data_str or f"{ano}-01-01",
                "categoria": categoria,
                "ano": ano,
            },
        )
        return jsonify({"success": True, "novo_arquivo": chave_nova})
    except Exception as error:
        return jsonify({"error": str(error)}), 500


@app.route("/api/excluir", methods=["POST"])
def excluir():
    data = request.json
    if not data or "arquivo" not in data:
        return jsonify({"error": "Dados inválidos."}), 400

    try:
        arquivo_relativo, arquivo = resolve_document_file(data["arquivo"])
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 404

    recovery_dir = EXPORT_DIR / RECOVERY_FOLDER / datetime.now().strftime("%Y%m%d-%H%M%S")
    target = unique_path(recovery_dir / Path(arquivo_relativo).name)
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        shutil.move(arquivo, target)
        cleanup_document_metadata(arquivo_relativo)
        sync_data()
        return jsonify({
            "success": True,
            "arquivo_recuperacao": target.relative_to(EXPORT_DIR).as_posix(),
        })
    except Exception as error:
        return jsonify({"error": str(error)}), 500


def normalize_export_documents(data):
    documents = data.get("documentos")
    if isinstance(documents, list):
        return [item for item in documents if isinstance(item, dict) and str(item.get("arquivo", "")).strip()]
    return []


def create_metadata_workbook(documents):
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Documentos"
    sheet.append(["Nome", "Assunto", "Categoria", "Data"])
    for doc in documents:
        sheet.append([doc.get("nome", ""), doc.get("assunto", ""), doc.get("categoria", ""), doc.get("data", "")])
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


@app.route("/api/exportar", methods=["POST"])
def exportar():
    documents = normalize_export_documents(request.get_json(silent=True) or {})
    if not documents:
        return jsonify({"error": "Nenhum documento selecionado."}), 400

    resolved = []
    try:
        for doc in documents:
            arquivo, file_path = resolve_document_file(doc.get("arquivo", ""))
            resolved.append(({**doc, "arquivo": arquivo}, file_path))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 404

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for doc, file_path in resolved:
            archive.write(file_path, doc["arquivo"])
        archive.writestr("informacoes_documentos.xlsx", create_metadata_workbook([doc for doc, _ in resolved]).getvalue())

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"portfolio-documentos-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip",
    )


@app.route("/api/gerar-pacote-publico", methods=["POST"])
def gerar_pacote_publico():
    try:
        output = create_public_package_for_runtime()
        return jsonify({"success": True, "path": str(output)})
    except Exception as error:
        print(f"[ERRO] Falha ao gerar pacote publico: {error}")
        return jsonify({"error": str(error)}), 500


def schedule_admin_browser(host: str, port: int) -> None:
    if os.environ.get("PORTFOLIO_OPEN_BROWSER") == "0":
        return
    if not getattr(sys, "frozen", False) and os.environ.get("PORTFOLIO_OPEN_BROWSER") != "1":
        return

    def open_browser():
        webbrowser.open(f"http://{host}:{port}/admin/")

    threading.Timer(1.0, open_browser).start()


if __name__ == "__main__":
    ensure_initial_catalog()
    print("=" * 60)
    print("Servidor de Administração Local do Portfólio")
    print("  Administração: http://localhost:5000/admin/")
    print("=" * 60)
    host = os.environ.get("PORTFOLIO_HOST", "127.0.0.1")
    port = int(os.environ.get("PORTFOLIO_PORT", "5000"))
    schedule_admin_browser(host, port)
    app.run(host=host, port=port)

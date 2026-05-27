import os
import re
import json
import shutil
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, redirect, send_file
from app_runtime import ensure_data_layout, get_runtime, load_app_config, save_app_config

RUNTIME = get_runtime()
ensure_data_layout(RUNTIME)

ROOT = RUNTIME.resource_dir
SITE_DIR = RUNTIME.site_dir
EXPORT_DIR = RUNTIME.documentos_dir
PUBLIC_SITE_DIR = RUNTIME.public_site_dir
ADMIN_SITE_DIR = RUNTIME.admin_site_dir

app = Flask(__name__, static_folder=None)

CATEGORIES_FILE = SITE_DIR / "categorias.json"

def load_categories():
    if not CATEGORIES_FILE.exists():
        return []
    try:
        data = json.loads(CATEGORIES_FILE.read_text("utf-8"))
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def save_categories(categories):
    CATEGORIES_FILE.write_text(json.dumps(categories, ensure_ascii=False, indent=2), "utf-8")

def safe_filename(s):
    """Remove caracteres inválidos para nomes de arquivos no Windows."""
    return re.sub(r'[\\/*?:"<>|]', "", s).strip()


def normalize_categoria_folder(categoria: str) -> str:
    """Normaliza o nome da categoria para o nome correto da pasta no disco.
    Evita problemas como ter 'CargoFunção' e 'Cargo-Função' ao mesmo tempo.
    """
    cat = safe_filename(categoria)
    # Mapeamentos para unificar variações antigas
    if cat in ("Cargo/Função", "CargoFunção", "Cargo - Função", "Cargofunção"):
        return "Cargo-Função"
    return cat

def update_pdf_metadata(file_path, novo_nome, novo_assunto):
    """Atualiza as propriedades físicas do arquivo PDF (Título e Assunto)."""
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
            
        new_meta.update({
            '/Title': novo_nome,
            '/Subject': novo_assunto
        })
        writer.add_metadata(new_meta)
        
        temp_path = file_path.with_suffix('.tmp.pdf')
        with open(temp_path, "wb") as f:
            writer.write(f)
            
        shutil.move(temp_path, file_path)
        return True
    except Exception as e:
        print(f"[AVISO] Não foi possível atualizar metadados do PDF {file_path.name}: {e}")
        return False

@app.route('/')
def index():
    return redirect('/portfolio/')

# Specific routes MUST come before the broad catch-all below
@app.route('/Documentos/<path:filename>')
def serve_documentos(filename):
    return send_from_directory(EXPORT_DIR, filename)


def normalize_export_documents(data):
    documents = data.get("documentos")
    if isinstance(documents, list):
        return [
            item for item in documents
            if isinstance(item, dict) and str(item.get("arquivo", "")).strip()
        ]

    arquivos = data.get("arquivos")
    if isinstance(arquivos, list):
        return [
            {
                "nome": "",
                "assunto": "",
                "categoria": "",
                "ano": "",
                "data": "",
                "numero": "",
                "arquivo": str(arquivo),
            }
            for arquivo in arquivos
            if str(arquivo).strip()
        ]

    return []


def resolve_export_file(arquivo):
    if not isinstance(arquivo, str):
        raise ValueError("Arquivo inválido.")

    normalized = arquivo.replace("\\", "/").strip()
    if not normalized or normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        raise ValueError("Caminho de arquivo inválido.")

    candidate = (EXPORT_DIR / normalized).resolve()
    export_root = EXPORT_DIR.resolve()

    if export_root != candidate and export_root not in candidate.parents:
        raise ValueError("Caminho de arquivo inválido.")
    if not candidate.is_file():
        raise FileNotFoundError("Arquivo não encontrado.")

    return normalized, candidate


def create_metadata_workbook(documents):
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Documentos"
    sheet.append(["Nome", "Assunto", "Categoria", "Data"])

    for doc in documents:
        sheet.append([
            doc.get("nome", ""),
            doc.get("assunto", ""),
            doc.get("categoria", ""),
            format_excel_date(doc.get("data", "")),
        ])

    for column_cells in sheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        sheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 60)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def format_excel_date(value):
    text = str(value or "").strip()
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if not match:
        return text
    year, month, day = match.groups()
    return f"{day}-{month}-{year}"


@app.route('/api/exportar', methods=['POST'])
def exportar():
    data = request.get_json(silent=True) or {}
    documents = normalize_export_documents(data)

    if not documents:
        return jsonify({"error": "Nenhum documento selecionado."}), 400

    resolved = []
    try:
        for doc in documents:
            arquivo, file_path = resolve_export_file(doc.get("arquivo", ""))
            export_doc = {
                "nome": doc.get("nome", ""),
                "assunto": doc.get("assunto", ""),
                "categoria": doc.get("categoria", ""),
                "ano": doc.get("ano", ""),
                "data": doc.get("data", ""),
                "numero": doc.get("numero", ""),
                "arquivo": arquivo,
            }
            resolved.append((export_doc, file_path))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for doc, file_path in resolved:
            archive.write(file_path, doc["arquivo"])

        metadata = create_metadata_workbook([doc for doc, _ in resolved])
        archive.writestr("informacoes_documentos.xlsx", metadata.getvalue())

    zip_buffer.seek(0)
    filename = f"portfolio-documentos-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename,
    )


@app.route('/api/gerar-pacote-publico', methods=['POST'])
def gerar_pacote_publico():
    from create_public_package import create_public_package

    output = RUNTIME.data_dir / "dist-publico"
    create_public_package(RUNTIME.data_dir, output, public_site_dir=PUBLIC_SITE_DIR)
    return jsonify({"success": True, "path": str(output)})

# --- Public frontend ---
@app.route('/portfolio/')
@app.route('/portfolio/<path:filename>')
def serve_public_site(filename=None):
    if filename is None:
        filename = 'index.html'
    return send_from_directory(PUBLIC_SITE_DIR, filename)


# --- Administration frontend ---
@app.route('/admin/')
@app.route('/admin/<path:filename>')
def serve_admin_site(filename=None):
    if filename is None:
        filename = 'index.html'
    return send_from_directory(ADMIN_SITE_DIR, filename)


# Shared data files (dados.js, edicoes.json, ocultos.json) for the new frontend
# when accessed via the server
@app.route('/shared-data/dados.js')
def serve_shared_dados():
    return send_from_directory(SITE_DIR, 'dados.js')

@app.route('/shared-data/config.json')
def serve_shared_config():
    return jsonify(load_app_config(RUNTIME))

@app.route('/shared-data/<path:filename>')
def serve_shared_data(filename):
    # Only the files the public viewer needs for overrides
    if filename not in ('edicoes.json', 'ocultos.json', 'categorias.json'):
        return "Forbidden", 403
    return send_from_directory(SITE_DIR, filename)


@app.route('/api/config', methods=['GET'])
def app_config():
    return jsonify(load_app_config(RUNTIME))


@app.route('/api/abrir-documentos', methods=['POST'])
def abrir_documentos():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        return jsonify({"error": "Abertura de pasta disponivel apenas no Windows."}), 400
    os.startfile(str(EXPORT_DIR))
    return jsonify({"success": True})


@app.route('/api/categorias', methods=['GET', 'POST'])
def categorias():
    if request.method == 'GET':
        return jsonify(load_categories())


    data = request.get_json() or {}
    nome = re.sub(r'\s+', ' ', data.get('nome', '')).strip()
    color = data.get('color', '#546E7A').strip() or '#546E7A'

    if not nome:
        return jsonify({"error": "Informe o nome da categoria."}), 400

    if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        return jsonify({"error": "Cor inválida."}), 400

    categories = load_categories()
    if any((item.get('nome', '') or '').lower() == nome.lower() for item in categories if isinstance(item, dict)):
        return jsonify({"error": "Essa categoria já existe."}), 409

    categories.append({"nome": nome, "color": color})
    categories.sort(key=lambda item: item.get('nome', '').lower())
    save_categories(categories)
    return jsonify(categories)


@app.route('/api/ocultar', methods=['POST'])
def ocultar():

    data = request.json
    if not data or 'arquivo' not in data:
        return jsonify({"error": "Dados inválidos."}), 400
        
    arquivo = data['arquivo']
    estado_oculto = data.get('oculto', True)
    
    ocultos_file = SITE_DIR / "ocultos.json"
    import json
    ocultos = []
    if ocultos_file.exists():
        try:
            ocultos = json.loads(ocultos_file.read_text("utf-8"))
        except Exception:
            pass
            
    if estado_oculto:
        if arquivo not in ocultos:
            ocultos.append(arquivo)
    else:
        if arquivo in ocultos:
            ocultos.remove(arquivo)
            
    ocultos_file.write_text(json.dumps(ocultos, ensure_ascii=False, indent=2), "utf-8")
    
    try:
        # ATENÇÃO: Não rodamos mais o gerar_dados.py aqui!
        # A sincronização será feita pelo botão do painel.
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sync', methods=['POST'])
def sync_db():

    try:
        print("[INFO] Sincronização manual iniciada. Gerando dados no processo atual...")
        from gerar_dados import main as gerar_dados_main
        gerar_dados_main()
        print("[OK] dados.js atualizado com sucesso via sync.")
        return jsonify({"success": True})
    except Exception as e:
        print(f"[ERRO] Falha inesperada ao sincronizar: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload():

    file = request.files.get('file')
    if not file:
        return jsonify({"error": "Nenhum arquivo enviado."}), 400

    nome = request.form.get('nome', '').strip()
    assunto = request.form.get('assunto', '').strip()
    categoria = request.form.get('categoria', '').strip()
    ano = request.form.get('ano', '').strip()
    data = request.form.get('data', '').strip() or f"{ano}-01-01"
    numero = request.form.get('numero', '').strip()

    if not nome or not ano or not categoria:
        return jsonify({"error": "Dados obrigatórios ausentes."}), 400

    novo_nome_base = safe_filename(nome)
    if assunto:
        novo_nome_base += f" - {safe_filename(assunto)}"
    novo_nome_base += ".pdf"

    nova_categoria = normalize_categoria_folder(categoria)

    nova_pasta = EXPORT_DIR / safe_filename(nova_categoria) / safe_filename(ano)
    nova_pasta.mkdir(parents=True, exist_ok=True)
    
    arquivo_novo = nova_pasta / novo_nome_base
    
    counter = 1
    while arquivo_novo.exists():
        novo_nome_base = f"{arquivo_novo.stem} ({counter}).pdf"
        arquivo_novo = nova_pasta / novo_nome_base
        counter += 1

    file.save(arquivo_novo)
    
    # Atualiza as propriedades internas do PDF
    update_pdf_metadata(arquivo_novo, nome, assunto)
    
    try:
        print(f"[INFO] Arquivo salvo e importado: {arquivo_novo}")
        # ATENÇÃO: Não rodamos mais o gerar_dados.py aqui!
        # A sincronização será feita pelo botão do painel.
        
        novo_arquivo_relativo = arquivo_novo.relative_to(EXPORT_DIR).as_posix()
        # Salva o arquivo como uma "edição" para garantir os metadados do import até o sync
        edicoes_file = SITE_DIR / "edicoes.json"
        edicoes = {}
        if edicoes_file.exists():
            try:
                edicoes = json.loads(edicoes_file.read_text("utf-8"))
            except Exception:
                pass
        edicoes[novo_arquivo_relativo] = {
            "nome": nome,
            "assunto": assunto,
            "numero": numero,
            "data": data,
            "categoria": categoria
        }
        edicoes_file.write_text(json.dumps(edicoes, ensure_ascii=False, indent=2), "utf-8")
        
        return jsonify({"success": True, "novo_arquivo": novo_arquivo_relativo})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/editar', methods=['POST'])
def editar():

    data = request.json
    if not data or 'arquivo' not in data:
        return jsonify({"error": "Dados inválidos."}), 400

    arquivo_relativo = data['arquivo']
    arquivo_antigo = EXPORT_DIR / arquivo_relativo
    
    if not arquivo_antigo.exists():
        return jsonify({"error": "Arquivo original não encontrado no diretório."}), 404

    nome = data.get('nome', '').strip()
    assunto = data.get('assunto', '').strip()
    categoria = data.get('categoria', '').strip()
    
    # Tenta extrair o ano da data (YYYY-MM-DD), senão usa o diretório pai atual
    data_str = data.get('data', '')
    ano = data_str.split('-')[0] if data_str else arquivo_antigo.parent.name
    
    # Monta o novo nome base no formato que o gerar_dados.py entende: Nome - Assunto.pdf
    novo_nome_base = safe_filename(nome)
    if assunto:
        novo_nome_base += f" - {safe_filename(assunto)}"
    novo_nome_base += ".pdf"
    
    # Determina a nova pasta com base na categoria
    nova_categoria = normalize_categoria_folder(categoria)
        
    nova_pasta = EXPORT_DIR / safe_filename(nova_categoria) / safe_filename(ano)
    nova_pasta.mkdir(parents=True, exist_ok=True)
    
    arquivo_novo = nova_pasta / novo_nome_base
    
    try:
        if arquivo_antigo != arquivo_novo:
            # Tratamento de colisões
            counter = 1
            while arquivo_novo.exists() and arquivo_novo != arquivo_antigo:
                novo_nome_base = f"{arquivo_novo.stem} ({counter}).pdf"
                arquivo_novo = nova_pasta / novo_nome_base
                counter += 1
                
            shutil.move(arquivo_antigo, arquivo_novo)
            print(f"[OK] Arquivo renomeado:\nDe: {arquivo_antigo}\nPara: {arquivo_novo}")
            
        # Atualiza as propriedades internas do PDF
        update_pdf_metadata(arquivo_novo, nome, assunto)
            
        # Salvar edições no edicoes.json (para forçar o assunto/nome exato digitado)
        edicoes_file = SITE_DIR / "edicoes.json"
        edicoes = {}
        if edicoes_file.exists():
            try:
                edicoes = json.loads(edicoes_file.read_text("utf-8"))
            except Exception:
                pass
                
        # Remove a entrada antiga se foi renomeado
        chave_antiga = arquivo_antigo.relative_to(EXPORT_DIR).as_posix()
        chave_nova = arquivo_novo.relative_to(EXPORT_DIR).as_posix()
        if chave_antiga in edicoes and chave_antiga != chave_nova:
            del edicoes[chave_antiga]
            
        edicoes[chave_nova] = {
            "nome": nome,
            "assunto": assunto,
            "numero": data.get('numero', '').strip(),
            "data": data_str,
            "categoria": categoria
        }
        edicoes_file.write_text(json.dumps(edicoes, ensure_ascii=False, indent=2), "utf-8")
        
        # ATENÇÃO: Não rodamos mais o gerar_dados.py aqui! 
        # O usuário fará isso pelo botão Sincronizar.
        return jsonify({"success": True, "novo_arquivo": chave_nova})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("="*60)
    print("Servidor de Administração Local do Portfólio IFMG")
    print("  • Site público:   http://localhost:5000/portfolio/")
    print("  • Administração:  http://localhost:5000/admin/")
    print("="*60)
    print()
    host = os.environ.get("PORTFOLIO_HOST", "127.0.0.1")
    port = int(os.environ.get("PORTFOLIO_PORT", "5000"))
    print(f"[INFO] Servidor iniciando em http://{host}:{port} ...")
    print()
    app.run(host=host, port=port)

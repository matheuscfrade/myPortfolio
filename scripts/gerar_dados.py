"""
gerar_dados.py — Script único para gerar dados do portfólio.

 Lê a pasta Documentos/ (Categoria/Ano/arquivo.pdf),
extrai metadados de cada PDF e gera site/dados.js.
"""

import json
import re
import hashlib
from pathlib import Path
from app_runtime import ensure_data_layout, get_runtime

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

RUNTIME = get_runtime()
ensure_data_layout(RUNTIME)

ROOT = RUNTIME.resource_dir
EXPORT_DIR = RUNTIME.documentos_dir
OCULTOS_FILE = RUNTIME.site_dir / "ocultos.json"
OUTPUT = RUNTIME.site_dir / "dados.js"

MONTHS_PT = {
    "janeiro": "01", "fevereiro": "02", "março": "03", "marco": "03",
    "abril": "04", "maio": "05", "junho": "06", "julho": "07",
    "agosto": "08", "setembro": "09", "outubro": "10",
    "novembro": "11", "dezembro": "12",
}

CATEGORY_PRIORITY = [
    "Cargo/Função", "Conselho Superior", "Colegiado",
    "Fiscal de Contrato", "Comissão", "Grupo de Trabalho",
    "Progressão", "Outro",
]


def parse_date_from_filename(filename: str) -> str:
    """Extrai data ISO do nome do arquivo."""
    m = re.search(
        r"de\s+(\d{1,2})\s+de\s+([a-zçã]+)\s+de\s+(\d{4})",
        filename, re.I,
    )
    if m:
        day = m.group(1).zfill(2)
        month = MONTHS_PT.get(m.group(2).lower(), "")
        year = m.group(3)
        if month:
            return f"{year}-{month}-{day}"
    return ""


def parse_number_from_filename(filename: str) -> str:
    """Extrai número da portaria do nome do arquivo."""
    m = re.search(r"[Nn][ºo.]?\s*(\d+)", filename)
    return m.group(1) if m else ""


def extract_pdf_metadata(pdf_path: Path) -> dict:
    """Lê metadados gravados no PDF (Title, Subject, Keywords)."""
    if PdfReader is None:
        return {}
    try:
        reader = PdfReader(pdf_path)
        meta = reader.metadata
        if not meta:
            return {}
        return {
            "title": meta.get("/Title", ""),
            "subject": meta.get("/Subject", ""),
            "keywords": meta.get("/Keywords", ""),
        }
    except Exception:
        return {}


def extract_subject_from_content(pdf_path: Path) -> str:
    """Tenta extrair o assunto do conteúdo textual do PDF."""
    if PdfReader is None:
        return ""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages[:2]:
            text += page.extract_text() or ""
        # Limpa linhas de impressão
        lines = [l for l in text.split("\n")
                 if "Impresso em" not in l and "Criado no" not in l]
        text = "\n".join(lines)
        # Tenta achar "Dispõe sobre ..." ou "RESOLVE:" seguido de texto
        m = re.search(r"[Dd]isp[oõ]e\s+sobre\s+(.{20,200}?)(?:\.|$)", text)
        if m:
            return m.group(1).strip().rstrip(".")
        return ""
    except Exception:
        return ""


def catalog_folder(export_dir: Path) -> list[dict]:
    """Percorre Documentos/ e cataloga cada PDF."""
    records = []
    for pdf_path in sorted(export_dir.rglob("*.pdf")):
        rel = pdf_path.relative_to(export_dir)
        parts = rel.parts
        if len(parts) < 3:
            # Arquivo fora da estrutura Categoria/Ano/arquivo.pdf
            continue
        categoria_pasta = parts[0]
        # Mapear nomes de pasta para nomes de exibição
        # (Windows não permite / em nomes de pastas)
        FOLDER_MAP = {"Cargo-Função": "Cargo/Função"}

        # Normalização para unificar pastas antigas inconsistentes (ex: CargoFunção vs Cargo-Função)
        if categoria_pasta in ("CargoFunção", "Cargofunção"):
            categoria_pasta = "Cargo-Função"

        categoria = FOLDER_MAP.get(categoria_pasta, categoria_pasta)
        ano_pasta = parts[1]
        filename = pdf_path.name

        # Extrair dados do nome do arquivo
        data = parse_date_from_filename(filename)
        numero = parse_number_from_filename(filename)
        ano = int(ano_pasta) if ano_pasta.isdigit() else 0

        # Extrair metadados do PDF
        meta = extract_pdf_metadata(pdf_path)
        nome = meta.get("title", "") or pdf_path.stem
        assunto = meta.get("subject", "")

        # Se não tem assunto nos metadados, tenta do conteúdo
        if not assunto or assunto == "Assunto não encontrado":
            assunto = extract_subject_from_content(pdf_path)

        # Limpa assunto truncado
        if assunto and len(assunto) > 200:
            assunto = assunto[:197] + "..."

        records.append({
            "nome": nome,
            "assunto": assunto,
            "categoria": categoria,
            "ano": ano,
            "data": data or f"{ano_pasta}-01-01",
            "numero": numero,
            "arquivo": rel.as_posix(),
        })

    # Aplicar edições manuais (que sobrepõem qualquer dedução acima)
    edicoes_file = RUNTIME.site_dir / "edicoes.json"
    edicoes = {}
    if edicoes_file.exists():
        try:
            edicoes = json.loads(edicoes_file.read_text("utf-8"))
        except Exception:
            pass

    for rec in records:
        if rec["arquivo"] in edicoes:
            ed = edicoes[rec["arquivo"]]
            rec["nome"] = ed.get("nome", rec["nome"])
            rec["assunto"] = ed.get("assunto", rec["assunto"])
            rec["categoria"] = ed.get("categoria", rec["categoria"])
            rec["ano"] = int(ed.get("ano", rec["ano"])) if str(ed.get("ano", "")).isdigit() else rec["ano"]
            rec["data"] = ed.get("data", rec["data"])
            rec["numero"] = ed.get("numero", rec["numero"])

    # Marcar ocultos
    ocultos = []
    if OCULTOS_FILE.exists():
        try:
            ocultos = json.loads(OCULTOS_FILE.read_text("utf-8"))
        except Exception:
            pass

    for rec in records:
        if rec["arquivo"] in ocultos:
            rec["oculto"] = True

    return records


def deduplicate(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Remove duplicatas mantendo a categoria mais específica (não 'Outro').
    Retorna (mantidos, removidos)."""
    by_key: dict[str, dict] = {}
    removed = []
    priority = {cat: i for i, cat in enumerate(CATEGORY_PRIORITY)}

    for rec in records:
        # Chave: número + data completa (identifica unicamente uma portaria)
        key = f"{rec['numero']}_{rec['data']}"
        if not rec["numero"]:
            key = rec["arquivo"]  # fallback para arquivos sem número

        existing = by_key.get(key)
        if existing is None:
            by_key[key] = rec
        else:
            # Mantém a de categoria mais específica (menor índice na priority)
            old_pri = priority.get(existing["categoria"], 99)
            new_pri = priority.get(rec["categoria"], 99)
            if new_pri < old_pri:
                removed.append({"removido": existing, "mantido_como": rec, "chave": key})
                by_key[key] = rec
            else:
                removed.append({"removido": rec, "mantido_como": existing, "chave": key})

    return list(by_key.values()), removed


def generate_js(records: list[dict], output: Path, base_url: str = "",
                admin_hash: str = "") -> None:
    """Gera arquivo dados.js com os registros."""
    output.parent.mkdir(parents=True, exist_ok=True)
    js_data = json.dumps(records, ensure_ascii=False, indent=2)
    safe_url = json.dumps(base_url, ensure_ascii=False)
    safe_hash = json.dumps(admin_hash, ensure_ascii=False)
    output.write_text(
        f"// Gerado automaticamente por gerar_dados.py\n"
        f"// Fonte: Documentos/\n"
        f"// Total: {len(records)} documentos\n\n"
        f"const BASE_URL = {safe_url};\n"
        f"const ADMIN_HASH = {safe_hash};\n"
        f"const DOCUMENTOS = {js_data};\n",
        encoding="utf-8",
    )


def generate_duplicates_report(removed: list[dict], output: Path) -> None:
    """Gera relatório de duplicatas removidas."""
    lines = [
        "RELATÓRIO DE DUPLICATAS REMOVIDAS",
        "=" * 60,
        f"Total: {len(removed)} registros removidos por deduplicação",
        "",
    ]
    for i, entry in enumerate(removed, 1):
        rem = entry["removido"]
        kept = entry["mantido_como"]
        lines.append(f"--- Duplicata #{i} (chave: {entry['chave']}) ---")
        lines.append(f"  REMOVIDO:")
        lines.append(f"    Arquivo:    {rem['arquivo']}")
        lines.append(f"    Nome:       {rem['nome']}")
        lines.append(f"    Categoria:  {rem['categoria']}")
        lines.append(f"    Assunto:    {rem['assunto'][:100]}")
        lines.append(f"  MANTIDO COMO:")
        lines.append(f"    Arquivo:    {kept['arquivo']}")
        lines.append(f"    Nome:       {kept['nome']}")
        lines.append(f"    Categoria:  {kept['categoria']}")
        lines.append(f"    Assunto:    {kept['assunto'][:100]}")
        lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if not EXPORT_DIR.exists():
        print(f"Erro: Pasta {EXPORT_DIR} não encontrada.")
        return

    print("Lendo Documentos/...")
    records = catalog_folder(EXPORT_DIR)
    print(f"  {len(records)} PDFs encontrados")

    before = len(records)
    records, removed = deduplicate(records)
    if removed:
        print(f"  {len(removed)} duplicatas removidas")
        report_path = RUNTIME.site_dir / "duplicatas_removidas.txt"
        try:
            generate_duplicates_report(removed, report_path)
            print(f"  Relatório: {report_path}")
        except OSError as e:
            print(f"  [AVISO] Nao foi possivel atualizar o relatorio de duplicatas: {e}")

    # Ordenar por data (mais recente primeiro)
    records.sort(key=lambda r: r["data"], reverse=True)

    # Estatísticas
    categorias = {}
    anos = set()
    for rec in records:
        categorias[rec["categoria"]] = categorias.get(rec["categoria"], 0) + 1
        if rec["ano"]:
            anos.add(rec["ano"])

    print(f"\n  {len(records)} documentos únicos")
    print(f"  {len(categorias)} categorias:")
    for cat, count in sorted(categorias.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}")
    if anos:
        print(f"  Período: {min(anos)} – {max(anos)}")

    # Detectar flags
    base_url = "../Documentos/"
    admin_hash = ""
    for i, arg in enumerate(sys.argv):
        if arg == "--base-url" and i + 1 < len(sys.argv):
            base_url = sys.argv[i + 1]
            if not base_url.endswith("/"):
                base_url += "/"
            print(f"  Base URL: {base_url}")
        if arg == "--senha" and i + 1 < len(sys.argv):
            senha = sys.argv[i + 1]
            admin_hash = hashlib.sha256(senha.encode()).hexdigest()
            print(f"  Senha admin configurada (hash: {admin_hash[:12]}...)")

    if not admin_hash:
        print("  [AVISO] Sem senha admin. Use --senha <senha> para habilitar modo admin.")

    generate_js(records, OUTPUT, base_url, admin_hash)
    print(f"\nArquivo gerado: {OUTPUT}")

    if "--verificar" in sys.argv:
        verify_metadata(records)


def verify_metadata(records: list[dict]) -> None:
    """Verifica metadados comparando dados do registro com conteúdo real do PDF."""
    if PdfReader is None:
        print("\n[AVISO] pypdf não disponível — verificação ignorada.")
        return

    print("\nVerificando metadados vs conteúdo dos PDFs...")
    issues = []
    checked = 0

    for rec in records:
        pdf_path = EXPORT_DIR / rec["arquivo"]
        if not pdf_path.exists():
            issues.append({
                "arquivo": rec["arquivo"],
                "tipo": "ARQUIVO_AUSENTE",
                "detalhe": "PDF não encontrado no disco",
            })
            continue

        checked += 1
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages[:2]:
                text += page.extract_text() or ""

            # Limpar linhas de impressão
            lines = [l for l in text.split("\n")
                     if "Impresso em" not in l and "Criado no" not in l]
            clean = "\n".join(lines)

            # Verificar número
            num_match = re.search(
                r"PORTARIA\s+(?:N[ºo.]*\s*)?([0-9.]+)", clean, re.I
            )
            if num_match and rec["numero"]:
                pdf_num = num_match.group(1).replace(".", "").lstrip("0")
                rec_num = rec["numero"].lstrip("0")
                if pdf_num != rec_num:
                    issues.append({
                        "arquivo": rec["arquivo"],
                        "tipo": "NUMERO_DIVERGENTE",
                        "detalhe": f"Registro: {rec['numero']} | PDF: {num_match.group(1)}",
                    })

            # Verificar data
            date_match = re.search(
                r"(\d{1,2})\s+de\s+([A-Za-zçÇ]+)\s+de\s+(\d{4})", clean, re.I
            )
            if date_match and rec["data"] and not rec["data"].endswith("-01-01"):
                month_map = {
                    "janeiro":"01","fevereiro":"02","março":"03","marco":"03",
                    "abril":"04","maio":"05","junho":"06","julho":"07",
                    "agosto":"08","setembro":"09","outubro":"10",
                    "novembro":"11","dezembro":"12",
                }
                day = date_match.group(1).zfill(2)
                m = month_map.get(date_match.group(2).lower(), "")
                year = date_match.group(3)
                if m:
                    pdf_date = f"{year}-{m}-{day}"
                    if pdf_date != rec["data"]:
                        issues.append({
                            "arquivo": rec["arquivo"],
                            "tipo": "DATA_DIVERGENTE",
                            "detalhe": f"Registro: {rec['data']} | PDF: {pdf_date}",
                        })

            # Verificar assunto vazio
            if not rec["assunto"]:
                issues.append({
                    "arquivo": rec["arquivo"],
                    "tipo": "ASSUNTO_VAZIO",
                    "detalhe": "Nenhum assunto encontrado (metadados e conteúdo)",
                })

        except Exception as e:
            issues.append({
                "arquivo": rec["arquivo"],
                "tipo": "ERRO_LEITURA",
                "detalhe": str(e),
            })

    # Gerar relatório
    report_path = RUNTIME.site_dir / "verificacao_metadados.txt"
    report_lines = [
        "RELATÓRIO DE VERIFICAÇÃO: METADADOS vs CONTEÚDO DOS PDFs",
        "=" * 60,
        f"PDFs verificados: {checked}",
        f"Inconsistências encontradas: {len(issues)}",
        "",
    ]

    if not issues:
        report_lines.append("✅ Nenhuma inconsistência encontrada!")
    else:
        by_type: dict[str, list] = {}
        for issue in issues:
            by_type.setdefault(issue["tipo"], []).append(issue)

        for tipo, items in by_type.items():
            report_lines.append(f"\n{'='*40}")
            report_lines.append(f"  {tipo} ({len(items)} ocorrências)")
            report_lines.append(f"{'='*40}")
            for item in items:
                report_lines.append(f"  Arquivo: {item['arquivo']}")
                report_lines.append(f"  Detalhe: {item['detalhe']}")
                report_lines.append("")

    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"  {checked} PDFs verificados, {len(issues)} inconsistências")
    print(f"  Relatório: {report_path}")


import sys

if __name__ == "__main__":
    main()

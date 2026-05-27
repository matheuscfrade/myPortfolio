import json
import re
import hashlib
import sys
from pathlib import Path

from app_runtime import ensure_data_layout, get_runtime

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


RUNTIME = get_runtime()
ensure_data_layout(RUNTIME)

EXPORT_DIR = RUNTIME.documentos_dir
OCULTOS_FILE = RUNTIME.site_dir / "ocultos.json"
OUTPUT = RUNTIME.site_dir / "dados.js"

MONTHS_PT = {
    "janeiro": "01",
    "fevereiro": "02",
    "marco": "03",
    "março": "03",
    "abril": "04",
    "maio": "05",
    "junho": "06",
    "julho": "07",
    "agosto": "08",
    "setembro": "09",
    "outubro": "10",
    "novembro": "11",
    "dezembro": "12",
}

CATEGORY_PRIORITY = [
    "Cargo/Função",
    "Conselho Superior",
    "Colegiado",
    "Fiscal de Contrato",
    "Comissão",
    "Grupo de Trabalho",
    "Progressão",
    "Não Categorizado",
    "Outro",
]


def parse_date_from_filename(filename: str) -> str:
    match = re.search(
        r"de\s+(\d{1,2})\s+de\s+([a-zçã]+)\s+de\s+(\d{4})",
        filename,
        re.I,
    )
    if not match:
        return ""
    day = match.group(1).zfill(2)
    month = MONTHS_PT.get(match.group(2).lower(), "")
    year = match.group(3)
    return f"{year}-{month}-{day}" if month else ""


def parse_number_from_filename(filename: str) -> str:
    match = re.search(r"[Nn][ºo.]?\s*(\d+)", filename)
    return match.group(1) if match else ""


def extract_pdf_metadata(pdf_path: Path) -> dict:
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
        }
    except Exception:
        return {}


def extract_subject_from_content(pdf_path: Path) -> str:
    if PdfReader is None:
        return ""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages[:2]:
            text += page.extract_text() or ""
        lines = [
            line for line in text.split("\n")
            if "Impresso em" not in line and "Criado no" not in line
        ]
        match = re.search(r"[Dd]isp[oõ]e\s+sobre\s+(.{20,200}?)(?:\.|$)", "\n".join(lines))
        return match.group(1).strip().rstrip(".") if match else ""
    except Exception:
        return ""


def get_folder_metadata(rel: Path) -> tuple[str, int]:
    folder_map = {"Cargo-Função": "Cargo/Função"}
    parts = rel.parts

    if len(parts) >= 3:
        if parts[0] == "_Excluidos":
            return "", 0
        category_folder = parts[0]
        if category_folder in ("CargoFunção", "Cargofunção"):
            category_folder = "Cargo-Função"
        category = folder_map.get(category_folder, category_folder)
        year = int(parts[1]) if parts[1].isdigit() else 0
        return category, year

    if len(parts) == 2 and parts[1].lower().endswith(".pdf"):
        if parts[0] == "_Excluidos":
            return "", 0
        category_folder = parts[0]
        if category_folder in ("CargoFunção", "Cargofunção"):
            category_folder = "Cargo-Função"
        return folder_map.get(category_folder, category_folder), 0

    return "Não Categorizado", 0


def catalog_folder(export_dir: Path) -> list[dict]:
    records = []
    for pdf_path in sorted(export_dir.rglob("*.pdf")):
        rel = pdf_path.relative_to(export_dir)
        category, folder_year = get_folder_metadata(rel)
        if not category:
            continue
        filename = pdf_path.name
        date = parse_date_from_filename(filename)
        number = parse_number_from_filename(filename)
        year_from_date = int(date[:4]) if date[:4].isdigit() else 0
        year = folder_year or year_from_date

        meta = extract_pdf_metadata(pdf_path)
        subject = meta.get("subject", "") or extract_subject_from_content(pdf_path)
        if subject and len(subject) > 200:
            subject = subject[:197] + "..."

        records.append({
            "nome": meta.get("title", "") or pdf_path.stem,
            "assunto": subject,
            "categoria": category,
            "ano": year,
            "data": date or (f"{year}-01-01" if year else ""),
            "numero": number,
            "arquivo": rel.as_posix(),
        })

    edicoes_file = RUNTIME.site_dir / "edicoes.json"
    edicoes = {}
    if edicoes_file.exists():
        try:
            edicoes = json.loads(edicoes_file.read_text("utf-8"))
        except Exception:
            pass

    for record in records:
        edit = edicoes.get(record["arquivo"])
        if not edit:
            continue
        record["nome"] = edit.get("nome", record["nome"])
        record["assunto"] = edit.get("assunto", record["assunto"])
        record["categoria"] = edit.get("categoria", record["categoria"])
        record["ano"] = int(edit.get("ano", record["ano"])) if str(edit.get("ano", "")).isdigit() else record["ano"]
        record["data"] = edit.get("data", record["data"])
        record["numero"] = edit.get("numero", record["numero"])

    ocultos = []
    if OCULTOS_FILE.exists():
        try:
            ocultos = json.loads(OCULTOS_FILE.read_text("utf-8"))
        except Exception:
            pass

    for record in records:
        if record["arquivo"] in ocultos:
            record["oculto"] = True

    return records


def deduplicate(records: list[dict]) -> tuple[list[dict], list[dict]]:
    by_key = {}
    removed = []
    priority = {category: index for index, category in enumerate(CATEGORY_PRIORITY)}

    for record in records:
        key = f"{record['numero']}_{record['data']}" if record["numero"] else record["arquivo"]
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = record
            continue

        old_priority = priority.get(existing["categoria"], 99)
        new_priority = priority.get(record["categoria"], 99)
        if new_priority < old_priority:
            removed.append({"removido": existing, "mantido_como": record, "chave": key})
            by_key[key] = record
        else:
            removed.append({"removido": record, "mantido_como": existing, "chave": key})

    return list(by_key.values()), removed


def generate_js(records: list[dict], output: Path, base_url: str = "", admin_hash: str = "") -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "// Gerado automaticamente por gerar_dados.py\n"
        "// Fonte: Documentos/\n"
        f"// Total: {len(records)} documentos\n\n"
        f"const BASE_URL = {json.dumps(base_url, ensure_ascii=False)};\n"
        f"const ADMIN_HASH = {json.dumps(admin_hash, ensure_ascii=False)};\n"
        f"const DOCUMENTOS = {json.dumps(records, ensure_ascii=False, indent=2)};\n",
        "utf-8",
    )


def generate_duplicates_report(removed: list[dict], output: Path) -> None:
    lines = [
        "RELATORIO DE DUPLICATAS REMOVIDAS",
        "=" * 60,
        f"Total: {len(removed)} registros removidos por deduplicacao",
        "",
    ]
    for index, entry in enumerate(removed, 1):
        removed_doc = entry["removido"]
        kept_doc = entry["mantido_como"]
        lines.append(f"--- Duplicata #{index} (chave: {entry['chave']}) ---")
        lines.append("  REMOVIDO:")
        lines.append(f"    Arquivo:    {removed_doc['arquivo']}")
        lines.append(f"    Nome:       {removed_doc['nome']}")
        lines.append(f"    Categoria:  {removed_doc['categoria']}")
        lines.append(f"    Assunto:    {removed_doc['assunto'][:100]}")
        lines.append("  MANTIDO COMO:")
        lines.append(f"    Arquivo:    {kept_doc['arquivo']}")
        lines.append(f"    Nome:       {kept_doc['nome']}")
        lines.append(f"    Categoria:  {kept_doc['categoria']}")
        lines.append(f"    Assunto:    {kept_doc['assunto'][:100]}")
        lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if not EXPORT_DIR.exists():
        print(f"Erro: Pasta {EXPORT_DIR} nao encontrada.")
        return

    print("Lendo Documentos/...")
    records = catalog_folder(EXPORT_DIR)
    print(f"  {len(records)} PDFs encontrados")

    records, removed = deduplicate(records)
    if removed:
        print(f"  {len(removed)} duplicatas removidas")
        report_path = RUNTIME.site_dir / "duplicatas_removidas.txt"
        try:
            generate_duplicates_report(removed, report_path)
            print(f"  Relatorio: {report_path}")
        except OSError as error:
            print(f"  [AVISO] Nao foi possivel atualizar o relatorio de duplicatas: {error}")

    records.sort(key=lambda item: item["data"], reverse=True)

    categories = {}
    years = set()
    for record in records:
        categories[record["categoria"]] = categories.get(record["categoria"], 0) + 1
        if record["ano"]:
            years.add(record["ano"])

    print(f"\n  {len(records)} documentos unicos")
    print(f"  {len(categories)} categorias:")
    for category, count in sorted(categories.items(), key=lambda item: -item[1]):
        print(f"    {category}: {count}")
    if years:
        print(f"  Periodo: {min(years)} - {max(years)}")

    base_url = "../Documentos/"
    admin_hash = ""
    for index, arg in enumerate(sys.argv):
        if arg == "--base-url" and index + 1 < len(sys.argv):
            base_url = sys.argv[index + 1]
            if not base_url.endswith("/"):
                base_url += "/"
            print(f"  Base URL: {base_url}")
        if arg == "--senha" and index + 1 < len(sys.argv):
            password = sys.argv[index + 1]
            admin_hash = hashlib.sha256(password.encode()).hexdigest()
            print(f"  Senha admin configurada (hash: {admin_hash[:12]}...)")

    if not admin_hash:
        print("  [AVISO] Sem senha admin. Use --senha <senha> para habilitar modo admin.")

    generate_js(records, OUTPUT, base_url, admin_hash)
    print(f"\nArquivo gerado: {OUTPUT}")

    if "--verificar" in sys.argv:
        verify_metadata(records)


def verify_metadata(records: list[dict]) -> None:
    if PdfReader is None:
        print("\n[AVISO] pypdf nao disponivel - verificacao ignorada.")
        return

    print("\nVerificando metadados vs conteudo dos PDFs...")
    issues = []
    checked = 0

    for record in records:
        pdf_path = EXPORT_DIR / record["arquivo"]
        if not pdf_path.exists():
            issues.append({
                "arquivo": record["arquivo"],
                "tipo": "ARQUIVO_AUSENTE",
                "detalhe": "PDF nao encontrado no disco",
            })
            continue

        checked += 1
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages[:2]:
                text += page.extract_text() or ""

            clean = "\n".join(
                line for line in text.split("\n")
                if "Impresso em" not in line and "Criado no" not in line
            )

            number_match = re.search(
                r"PORTARIA\s+(?:N[ºo.]*\s*)?([0-9.]+)",
                clean,
                re.I,
            )
            if number_match and record["numero"]:
                pdf_number = number_match.group(1).replace(".", "").lstrip("0")
                record_number = record["numero"].lstrip("0")
                if pdf_number != record_number:
                    issues.append({
                        "arquivo": record["arquivo"],
                        "tipo": "NUMERO_DIVERGENTE",
                        "detalhe": f"Registro: {record['numero']} | PDF: {number_match.group(1)}",
                    })

            date_match = re.search(
                r"(\d{1,2})\s+de\s+([A-Za-zçÇ]+)\s+de\s+(\d{4})",
                clean,
                re.I,
            )
            if date_match and record["data"] and not record["data"].endswith("-01-01"):
                day = date_match.group(1).zfill(2)
                month = MONTHS_PT.get(date_match.group(2).lower(), "")
                year = date_match.group(3)
                if month:
                    pdf_date = f"{year}-{month}-{day}"
                    if pdf_date != record["data"]:
                        issues.append({
                            "arquivo": record["arquivo"],
                            "tipo": "DATA_DIVERGENTE",
                            "detalhe": f"Registro: {record['data']} | PDF: {pdf_date}",
                        })

            if not record["assunto"]:
                issues.append({
                    "arquivo": record["arquivo"],
                    "tipo": "ASSUNTO_VAZIO",
                    "detalhe": "Nenhum assunto encontrado (metadados e conteudo)",
                })

        except Exception as error:
            issues.append({
                "arquivo": record["arquivo"],
                "tipo": "ERRO_LEITURA",
                "detalhe": str(error),
            })

    report_path = RUNTIME.site_dir / "verificacao_metadados.txt"
    report_lines = [
        "RELATORIO DE VERIFICACAO: METADADOS vs CONTEUDO DOS PDFs",
        "=" * 60,
        f"PDFs verificados: {checked}",
        f"Inconsistencias encontradas: {len(issues)}",
        "",
    ]

    if not issues:
        report_lines.append("Nenhuma inconsistencia encontrada.")
    else:
        by_type: dict[str, list] = {}
        for issue in issues:
            by_type.setdefault(issue["tipo"], []).append(issue)

        for issue_type, items in by_type.items():
            report_lines.append(f"\n{'=' * 40}")
            report_lines.append(f"  {issue_type} ({len(items)} ocorrencias)")
            report_lines.append(f"{'=' * 40}")
            for item in items:
                report_lines.append(f"  Arquivo: {item['arquivo']}")
                report_lines.append(f"  Detalhe: {item['detalhe']}")
                report_lines.append("")

    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"  {checked} PDFs verificados, {len(issues)} inconsistencias")
    print(f"  Relatorio: {report_path}")


if __name__ == "__main__":
    main()

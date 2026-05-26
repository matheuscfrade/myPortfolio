#!/usr/bin/env python3
"""
Script para unificar as pastas 'CargoFunção' e 'Cargo-Função'.

Uso:
    python scripts/migrate_cargo_funcao.py

Ele vai:
- Mover todos os PDFs de Documentos/CargoFunção/ para Documentos/Cargo-Função/
- Atualizar as chaves correspondentes em site/edicoes.json
"""
import shutil
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = ROOT / "Documentos"
EDICOES_FILE = ROOT / "site" / "edicoes.json"

OLD_FOLDER = "CargoFunção"
NEW_FOLDER = "Cargo-Função"

def main():
    old_path = EXPORT_DIR / OLD_FOLDER
    new_path = EXPORT_DIR / NEW_FOLDER

    if not old_path.exists():
        print(f"Pasta {old_path} não existe. Nada a fazer.")
        return

    print(f"Iniciando migração de '{OLD_FOLDER}' → '{NEW_FOLDER}'...")

    moved_files = []
    errors = []

    # 1. Mover arquivos
    for year_folder in old_path.iterdir():
        if not year_folder.is_dir():
            continue

        target_year = new_path / year_folder.name
        target_year.mkdir(parents=True, exist_ok=True)

        for pdf_file in year_folder.glob("*.pdf"):
            target_file = target_year / pdf_file.name

            if target_file.exists():
                print(f"  [AVISO] Arquivo já existe no destino, pulando: {target_file}")
                errors.append(str(target_file))
                continue

            try:
                shutil.move(str(pdf_file), str(target_file))
                old_relative = f"{OLD_FOLDER}/{year_folder.name}/{pdf_file.name}"
                new_relative = f"{NEW_FOLDER}/{year_folder.name}/{pdf_file.name}"
                moved_files.append((old_relative, new_relative))
                print(f"  ✓ Movido: {old_relative} → {new_relative}")
            except Exception as e:
                print(f"  [ERRO] Falha ao mover {pdf_file}: {e}")
                errors.append(str(pdf_file))

    # 2. Atualizar edicoes.json
    if moved_files and EDICOES_FILE.exists():
        print("\nAtualizando edicoes.json...")
        try:
            with open(EDICOES_FILE, "r", encoding="utf-8") as f:
                edicoes = json.load(f)

            updated = False
            for old_key, new_key in moved_files:
                if old_key in edicoes:
                    edicoes[new_key] = edicoes.pop(old_key)
                    updated = True
                    print(f"  ✓ Chave atualizada no edicoes.json: {old_key} → {new_key}")

            if updated:
                with open(EDICOES_FILE, "w", encoding="utf-8") as f:
                    json.dump(edicoes, f, ensure_ascii=False, indent=2)
                print("  edicoes.json atualizado com sucesso.")
            else:
                print("  Nenhuma chave relevante encontrada em edicoes.json.")

        except Exception as e:
            print(f"  [ERRO] Falha ao atualizar edicoes.json: {e}")
            errors.append("edicoes.json")

    # 3. Tentar remover a pasta antiga se estiver vazia
    try:
        # Remove pastas vazias recursivamente
        for year_folder in list(old_path.iterdir()):
            if year_folder.is_dir() and not any(year_folder.iterdir()):
                year_folder.rmdir()

        if not any(old_path.iterdir()):
            old_path.rmdir()
            print(f"\n✓ Pasta antiga '{OLD_FOLDER}' removida (estava vazia).")
    except Exception as e:
        print(f"\n[AVISO] Não foi possível remover a pasta antiga: {e}")

    print("\n=== Migração concluída ===")
    print(f"Arquivos movidos com sucesso: {len(moved_files)}")
    if errors:
        print(f"Erros encontrados: {len(errors)}")
        for err in errors:
            print(f"  - {err}")

    print("\nRecomendação: Após rodar este script, abra o Admin e clique em 'Sincronizar'.")


if __name__ == "__main__":
    main()

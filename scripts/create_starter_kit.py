#!/usr/bin/env python3
"""
create_starter_kit.py
Gera um pacote limpo (starter kit) para novas pessoas criarem seus próprios portfólios.

Uso:
  python scripts/create_starter_kit.py

Saída: portfolio-starter-kit.zip na raiz do projeto.
"""
import zipfile
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ZIP = ROOT / "portfolio-starter-kit.zip"

# Arquivos/pastas a INCLUIR (relativos à raiz)
INCLUDE = [
    "scripts/servidor_admin.py",
    "scripts/gerar_dados.py",
    "scripts/app_runtime.py",
    "scripts/create_public_package.py",
    "site-publico/",
    "admin/",
    "requirements.txt",
    "iniciar_admin.bat",
    "Gerar_Pasta_Publica.bat",
    "Abrir_Portfolio_Publico.bat",
    "README.md",
]

# Pastas/arquivos a EXCLUIR completamente (dados do usuário)
EXCLUDE_DIRS = {
    "Documentos",
    "site",           # contém dados gerados + overrides do usuário
    "__pycache__",
    ".git",
}

EXCLUDE_FILES = {
    "dados.js",
    "edicoes.json",
    "ocultos.json",
    "duplicatas_removidas.txt",
    "verificacao_metadados.txt",
}

def should_include(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    rel_posix = rel.as_posix()

    # Excluir diretórios inteiros
    for p in parts:
        if p in EXCLUDE_DIRS:
            return False

    # Excluir arquivos específicos
    if path.name in EXCLUDE_FILES:
        return False

    # Só incluímos o que está na lista INCLUDE (ou dentro das pastas listadas)
    for inc in INCLUDE:
        inc_clean = inc.rstrip("/")
        if rel_posix == inc_clean or rel_posix.startswith(inc_clean + "/"):
            return True
    return False

def main():
    print("Criando starter kit limpo...")

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ROOT):
            root_path = Path(root)

            # Remover diretórios excluídos da caminhada
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for file in files:
                full_path = root_path / file
                if should_include(full_path):
                    arcname = full_path.relative_to(ROOT)
                    zf.write(full_path, arcname)
                    print(f"  + {arcname}")

    print(f"\n[OK] Starter kit criado: {OUTPUT_ZIP}")
    print("   (Contém apenas o essencial do sistema + scripts. Sem seus dados pessoais.)")

if __name__ == "__main__":
    main()

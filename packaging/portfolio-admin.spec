# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


ROOT = Path.cwd()

datas = [
    (str(ROOT / "admin"), "admin"),
    (str(ROOT / "site-publico"), "site-publico"),
    (str(ROOT / "scripts" / "gerar_dados.py"), "scripts"),
    (str(ROOT / "scripts" / "app_runtime.py"), "scripts"),
    (str(ROOT / "scripts" / "create_public_package.py"), "scripts"),
]

a = Analysis(
    [str(ROOT / "scripts" / "servidor_admin.py")],
    pathex=[str(ROOT / "scripts")],
    binaries=[],
    datas=datas,
    hiddenimports=["pypdf", "openpyxl"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PortfolioProfissional",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PortfolioProfissional",
)

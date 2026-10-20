# -*- mode: python ; coding: utf-8 -*-
# Empacota o RPA de paralisações. O Chromium vai junto para o outro computador.
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

datas = [
    ("data/motivos.json", "data"),
    ("data/tipo-paralizacoes.md", "data"),
    (".env.example", "."),
    ("src/paralisacao/ui/static", "paralisacao/ui/static"),
]
binaries = []
hiddenimports = [
    "greenlet",
    "pyee",
    "flask",
    "keyring.backends.Windows",
    "openpyxl",
    "dotenv",
    "paralisacao.ui.app",
    "paralisacao.ui.paginas",
    "paralisacao.ui.execucao",
    "paralisacao.preparar",
    "paralisacao.resumo",
]
tmp = collect_all("playwright")
datas += tmp[0]
binaries += tmp[1]
hiddenimports += tmp[2]

_local = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ms-playwright"
_chrome = [d for d in _local.glob("chromium-*") if d.is_dir() and "headless" not in d.name]
_compativel = [d for d in _chrome if d.name == "chromium-1148"]
if not _compativel:
    raise SystemExit(
        "[spec] ERRO: chromium-1148 nao encontrado. "
        "Rode: .venv\\Scripts\\python.exe -m playwright install chromium"
    )
_src = _compativel[0]
datas += [(str(_src), f"playwright/driver/package/.local-browsers/{_src.name}")]
print(f"[spec] chromium embutido: {_src.name}")

a = Analysis(
    ["src/paralisacao/__main__.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tests", "pytest"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Paralisacoes",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    upx=False,
    upx_exclude=[],
    name="Paralisacoes",
)

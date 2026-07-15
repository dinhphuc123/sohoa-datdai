# -*- mode: python ; coding: utf-8 -*-
import sys
import os

# Auto-create default config.json if not present on clean CI checkout
if not os.path.exists('config.json'):
    with open('config.json', 'w', encoding='utf-8') as f:
        f.write('{\n  "ocr_mode": "gemini"\n}\n')

added_files = [
    ('assets', 'assets'),
    ('config.json', '.'),
]

hidden_imports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'fitz',
    'PIL',
    'PIL.Image',
    'sqlite3',
    'openpyxl',
    'reportlab',
    'requests',
    'json',
    'base64',
    're',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DatDaiDesktop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DatDaiDesktop',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='DatDaiDesktop.app',
        icon=None,
        bundle_identifier='com.datdaivn.desktop',
    )

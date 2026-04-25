# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec-bestand voor PandaPrice
# Gegenereerd voor onefile-modus met assets en hidden imports

import os

block_cipher = None

# Controleer of het icoon beschikbaar is
icon_path = os.path.join('src', 'bambu_price_calculator', 'assets', 'icon.ico')
icon = icon_path if os.path.exists(icon_path) else None

a = Analysis(
    ['src/bambu_price_calculator/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/bambu_price_calculator/assets', 'bambu_price_calculator/assets'),
    ],
    hiddenimports=[
        'sv_ttk',
        'darkdetect',
        'pystray',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'watchdog',
        'watchdog.observers',
        'watchdog.events',
        'requests',
        'semver',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PandaPrice',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
    onefile=True,
)

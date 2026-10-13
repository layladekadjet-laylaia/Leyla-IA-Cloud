# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['moteur_ia.py'],
    pathex=[],
    binaries=[],
    datas=[('config.toml', '.'), ('LOGO LAYLA.png', '.')],
    hiddenimports=[
        'bleak',
        'psycopg2',
        'sqlite3',
        'toml',
        'utils_actions',
        'utils_audit',
        'utils_adb',
        'utils_db',
        'utils_scan',
        'utils_systeme',
        'utils_memoire',
        'utils_config',
        'camera_leyla',
        'briefing_leyla',
        'auth_manager'
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
    name='Leyla_Edge_Agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='LOGO LAYLA.png'
)

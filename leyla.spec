# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# Liste des ressources statiques à embarquer
datas_list = [
    ('config.toml', '.'),
    ('requirements.txt', '.'),
    ('run_app.py', '.'),
    ('LOGO LAYLA.png', '.')
]

# Embarquement sécurisé du runtime PyArmor si généré
if os.path.exists('pyarmor_runtime'):
    datas_list.append(('pyarmor_runtime', 'pyarmor_runtime'))

a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=[],
    datas=datas_list,
    hiddenimports=[
        # Dépendances système et backends
        'bleak',
        'psycopg2',
        'sqlite3',
        'toml',
        'fastapi',
        'uvicorn',
        'websockets',
        'sounddevice',
        'scipy',
        'scipy.io.wavfile',
        'pygetwindow',
        'google.genai',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        # Modules applicatifs locaux
        'auth_manager',
        'briefing_leyla',
        'camera_leyla',
        'db_manager',
        'hub_leyla',
        'memoire_leyla',
        'moteur_ia',
        'recherche_ia',
        'secretaire_auto',
        'serveur_leyla',
        'utils_actions',
        'utils_audit',
        'utils_config',
        'utils_db',
        'utils_memoire',
        'utils_scan',
        'utils_systeme',
        'vision_leyla'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['serveur_central'],
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

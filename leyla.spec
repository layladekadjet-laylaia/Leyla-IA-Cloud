# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(
    ['run_app.py'],  # Point d'entrée principal orchestrant le Hub et Streamlit
    pathex=[],
    binaries=[],
    datas=[
        ('config.toml', '.'),         # Fichier de configuration modifiable par l'administrateur
        ('requirements.txt', '.'),    # Référence des dépendances
        ('run_app.py', '.'),          # Script de lancement
        ('LOGO LAYLA.png', '.'),      # Logo et filigrane officiel
        ('pyarmor_runtime', 'pyarmor_runtime') # Dossier de déchiffrement sécurisé de PyArmor
    ],
    hiddenimports=[
        # Dépendances techniques et matérielles
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
        # Modules fonctionnels, d'actions, d'audit et d'intelligence de Leyla
        'auth_manager',
        'briefing_leyla',
        'camera_leyla',
        'db_manager',
        'hub_leyla',
        'memoire_leyla',
        'moteur_ia',
        'recherche_ia',
        'secretaire_auto',
        'secretaire_leyla',
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
    excludes=['serveur_central'], # Exclu car réservé au Cloud / PDC central
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

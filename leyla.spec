# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_metadata

block_cipher = None

# Liste des ressources statiques et de TOUS les scripts .py à embarquer
datas_list = [
    ('config.toml', '.'),
    ('requirements.txt', '.'),
    ('run_app.py', '.'),
    ('moteur_ia.py', '.'),
    ('hub_leyla.py', '.'),
    ('recherche_ia.py', '.'),
    ('db_manager.py', '.'),
    ('auth_manager.py', '.'),
    ('briefing_leyla.py', '.'),
    ('camera_leyla.py', '.'),
    ('memoire_leyla.py', '.'),
    ('secretaire_auto.py', '.'),
    ('serveur_leyla.py', '.'),
    ('vision_leyla.py', '.'),
    ('utils_actions.py', '.'),
    ('utils_audit.py', '.'),
    ('utils_config.py', '.'),
    ('utils_db.py', '.'),
    ('utils_memoire.py', '.'),
    ('utils_scan.py', '.'),
    ('utils_systeme.py', '.'),
    ('LOGO LAYLA.png', '.')
]

# Collecte automatique indispensable des métadonnées de Streamlit
datas_list += collect_metadata('streamlit')

if os.path.exists('pyarmor_runtime'):
    datas_list.append(('pyarmor_runtime', 'pyarmor_runtime'))

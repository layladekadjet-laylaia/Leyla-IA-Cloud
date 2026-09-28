import os
import sys
import streamlit.web.cli as stcli

if __name__ == "__main__":
    # Résolution dynamique du dossier d'exécution et de l'exécutable
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
        exe_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        exe_dir = base_dir

    # Recherche de moteur_ia.py (dans _internal/sys._MEIPASS ou à côté du .exe)
    script_path = os.path.join(base_dir, "moteur_ia.py")
    if not os.path.exists(script_path):
        script_path = os.path.join(exe_dir, "moteur_ia.py")

    # Configuration des arguments Streamlit
    sys.argv = [
        "streamlit",
        "run",
        script_path,
        "--global.developmentMode=false",
        "--server.port=8501",
        "--server.headless=false",
        "--browser.serverAddress=localhost"
    ]

    sys.exit(stcli.main())

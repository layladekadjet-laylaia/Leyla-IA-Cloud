import os
import sys
import streamlit.web.cli as stcli

if __name__ == "__main__":
    # 1. Gestion du chemin absolu pour la compatibilité PyInstaller (.exe)
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. On pointe vers moteur_ia.py qui contient l'interface graphique Streamlit
    script_path = os.path.join(base_dir, "moteur_ia.py")

    # 3. Arguments de lancement natifs
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

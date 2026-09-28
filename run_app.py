import os
import sys
import streamlit.web.cli as stcli

if __name__ == "__main__":
    # Résolution dynamique des dossiers pour PyInstaller
    if getattr(sys, "frozen", False):
        base_dir = sys._MEIPASS
        exe_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        exe_dir = base_dir

    # Tentative de démarrage du Hub FastAPI en arrière-plan (Port 8000)
    try:
        import hub_leyla

        hub_leyla.demarrer_hub_arriere_plan()
        print("⚡ Hub Leyla démarré en arrière-plan sur le port 8000")
    except Exception as e:
        print(f"⚠️ Le Hub n'a pas pu être démarré en arrière-plan : {e}")

    # Recherche du script d'interface Streamlit (moteur_ia.py)
    script_path = os.path.join(base_dir, "moteur_ia.py")
    if not os.path.exists(script_path):
        script_path = os.path.join(exe_dir, "moteur_ia.py")

    # Arguments officiels pour le lancement de Streamlit (Port 8501)
    sys.argv = [
        "streamlit",
        "run",
        script_path,
        "--global.developmentMode=false",
        "--server.port=8501",
        "--server.headless=false",
        "--browser.serverAddress=localhost",
    ]

    # Démarrage de Streamlit
    sys.exit(stcli.main())

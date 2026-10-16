import os
import sys

if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        base_dir = sys._MEIPASS
        exe_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        exe_dir = base_dir

    # CRITIQUE : Injecter le dossier de base en tête de liste pour la résolution des modules
    sys.path.insert(0, base_dir)

# Pré-importations explicites pour forcer la détection des dépendances par PyInstaller
try:
    import PIL
    import PIL.Image
    import PIL.ImageDraw
    import PIL.ImageFont
    from google import genai
except ImportError:
    pass

if __name__ == "__main__":
    # 1. Lancement du Hub sur le port 8000 en arrière-plan
    try:
        import hub_leyla

        hub_leyla.demarrer_hub_arriere_plan()
        print("✅ Hub Leyla démarré sur le port 8000.")
    except Exception as e:
        print(f"⚠️ Lancement du Hub ignoré : {e}")

    # 2. Localisation robuste du script Streamlit (moteur_ia.py)
    script_path = os.path.join(base_dir, "moteur_ia.py")
    if not os.path.exists(script_path):
        script_path = os.path.join(exe_dir, "moteur_ia.py")

    # 3. Configuration des arguments pour Streamlit
    sys.argv = [
        "streamlit",
        "run",
        script_path,
        "--global.developmentMode=false",
        "--server.port=8501",
        "--server.headless=false",
        "--browser.serverAddress=localhost",
    ]

    import streamlit.web.cli as stcli

    sys.exit(stcli.main())

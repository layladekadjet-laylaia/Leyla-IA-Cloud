import os
import sys

# Pré-importation explicite pour forcer l'inclusion par PyInstaller
try:
    import PIL
    import PIL.Image
    import PIL.ImageDraw
    import PIL.ImageFont
except ImportError:
    pass

if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        base_dir = sys._MEIPASS
        exe_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        exe_dir = base_dir

    # 1. Lancement du Hub sur le port 8000 en arrière-plan
    try:
        import hub_leyla

        hub_leyla.demarrer_hub_arriere_plan()
        print("✅ Hub Leyla démarré sur le port 8000.")
    except Exception as e:
        print(f"⚠️ Lancement du Hub ignoré : {e}")

    # 2. Localisation du script Streamlit
    script_path = os.path.join(base_dir, "moteur_ia.py")
    if not os.path.exists(script_path):
        script_path = os.path.join(exe_dir, "moteur_ia.py")

    # 3. Préparation explicite des arguments Streamlit
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

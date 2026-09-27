import os
import sys
import streamlit.web.cli as stcli

if __name__ == "__main__":
    # Pointage direct vers votre fichier principal recherche_ia.py
    sys.argv = ["streamlit", "run", "recherche_ia.py", "--global.developmentMode=false"]
    sys.exit(stcli.main())

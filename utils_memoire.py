import os
import streamlit as st
from google import genai
from google.genai import types

def generer_resume(messages):
    """Génère un résumé de l'historique en utilisant Gemini"""
    api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    texte_a_resumer = ""
    for m in messages:
        role = "Utilisateur" if m["role"] == "user" else "Leyla"
        texte_a_resumer += f"{role} : {m['content']}\n"
        
    prompt = (
        f"Fais un résumé concis et factuel des points clés de cette discussion pour conserver "
        f"le contexte important :\n{texte_a_resumer}"
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=300,
            )
        )
        return response.text if response and response.text else "Résumé indisponible."
    except Exception as e:
        return f"Erreur lors du résumé : {str(e)}"

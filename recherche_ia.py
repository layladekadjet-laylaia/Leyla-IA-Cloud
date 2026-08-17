import os
import base64
from groq import Groq
from duckduckgo_search import DDGS

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def image_to_base64(image_file):
    """Convertit de manière sécurisée le fichier Streamlit en Base64"""
    try:
        if image_file is None: 
            return None
        if hasattr(image_file, "getvalue"):
            data = image_file.getvalue()
        elif hasattr(image_file, "read"):
            image_file.seek(0)
            data = image_file.read()
        else:
            return None
        return base64.b64encode(data).decode("utf-8")
    except Exception:
        return None

def rechercher_sur_le_web(historique, image_file=None):
    derniere_requete = historique[-1]["content"] if historique else ""
    contexte_web = ""
    try:
        with DDGS() as ddgs:
            resultats = [r for r in ddgs.text(derniere_requete, max_results=3)]
            for item in resultats:
                contexte_web += f"- {item.get('title', '')}: {item.get('body', '')}\n"
    except Exception:
        contexte_web = "Recherche web indisponible."

    message_systeme = {
        "role": "system", 
        "content": f"Tu es Leyla, l'IA de Djè Akadjé. Appelle-le 'Mon Professeur'. Voici des infos web : {contexte_web}"
    }
    
    messages_formates = [message_systeme]
    img_b64 = image_to_base64(image_file) if image_file else None
    
    for i, msg in enumerate(historique):
        if i == len(historique) - 1 and img_b64:
            messages_formates.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": msg["content"]},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]
            })
        else:
            messages_formates.append({"role": msg["role"], "content": msg["content"]})

    try:
        completion = client.chat.completions.create(
            model="meta-llama/llama-3.2-90b-instruct",
            messages=messages_formates,
            max_tokens=1024
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Erreur IA : {str(e)}"

import os
import base64
from groq import Groq
from duckduckgo_search import DDGS

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def image_to_base64(image_file):
    """Convertit le fichier image Streamlit en chaîne Base64"""
    try:
        image_file.seek(0)
        return base64.b64encode(image_file.read()).decode("utf-8")
    except Exception:
        return None

def rechercher_sur_le_web(historique, image_file=None):
    # Récupération du dernier message textuel de l'utilisateur
    derniere_requete = historique[-1]["content"] if historique else ""
    
    contexte_web = ""
    try:
        with DDGS() as ddgs:
            resultats = [r for r in ddgs.text(derniere_requete, max_results=3)]
            for item in resultats:
                titre = item.get("title", "")
                corps = item.get("body", "")
                contexte_web += f"- {titre}: {corps}\n"
    except Exception:
        contexte_web = "Aucune recherche internet disponible pour le moment."

    message_systeme = {
        "role": "system", 
        "content": (
            f"Tu es Leyla, l'IA intelligente et serviable de Djè Akadjé. "
            f"Ton créateur, ton concepteur et ton professeur est Djè Akadjé. "
            f"Tu dois impérativement l'appeler 'Mon Professeur'. "
            f"Voici des informations fraîches du web pour t'aider à répondre précisément : {contexte_web}"
        )
    }
    
    # Préparation des messages pour Groq
    messages_formates = [message_systeme]
    
    # On parcourt l'historique pour l'envoyer à l'API
    for i, msg in enumerate(historique):
        # Si c'est le tout dernier message utilisateur et qu'on a une image jointe
        if i == len(historique) - 1 and msg["role"] == "user" and image_file is not None:
            img_b64 = image_to_base64(image_file)
            if img_b64:
                # Format multimodal supporté par Llama 3.2 Vision chez Groq
                messages_formates.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": msg["content"]},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_b64}"
                            }
                        }
                    ]
                })
                continue
        
        # Messages classiques (texte seul)
        messages_formates.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    try:
        completion = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",  # Modèle multimodal compatible vision chez Groq
            messages=messages_formates,
            max_tokens=1024
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Erreur Cloud (Vision) : {e}"

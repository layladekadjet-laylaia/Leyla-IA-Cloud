import os
from groq import Groq
from duckduckgo_search import DDGS

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def rechercher_sur_le_web(historique):
    derniere_requete = historique[-1]["content"]
    
    contexte_web = ""
    try:
        with DDGS() as ddgs:
            resultats = [r for r in ddgs.text(derniere_requete, max_results=3)]
            for item in resultats:
                titre = item.get("title", "")
                corps = item.get("body", "")
                contexte_web += f"- {titre}: {corps}\n"
    except Exception as e:
        contexte_web = "Aucune recherche internet disponible pour le moment."

    message_systeme = {
        "role": "system", 
        "content": f"Tu es Leyla, l'IA intelligente et serviable de Djè Akadjé. Ton créateur, ton concepteur et ton professeur est Djè Akadjé. Tu dois impérativement l'appeler 'Mon Professeur'. Voici des informations fraîches du web pour t'aider à répondre précisément : {contexte_web}"
    }
    
    messages_complets = [message_systeme] + historique

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages_complets
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Erreur Cloud : {e}"

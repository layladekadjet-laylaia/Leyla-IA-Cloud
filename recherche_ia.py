import requests
import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def rechercher_sur_le_web(historique):
    # On récupère seulement la dernière question du professeur pour faire la recherche web
    derniere_requete = historique[-1]["content"]
    
    url_api = "https://fr.wikipedia.org/w/api.php"
    params = {"action": "query", "list": "search", "srsearch": derniere_requete, "format": "json", "srlimit": 2}
    headers = {'User-Agent': 'LeilaAssistant/1.0'}
    
    contexte_wiki = ""
    try:
        response = requests.get(url_api, params=params, headers=headers, timeout=5)
        data = response.json()
        search_results = data.get("query", {}).get("search", [])
        for item in search_results:
            snippet = item.get("snippet", "").replace('<span class="searchmatch">', "").replace('</span>', "")
            contexte_wiki += snippet + " "
    except:
        contexte_wiki = "Aucune recherche internet disponible."

    # On prépare le message système avec le contexte web
    message_systeme = {
        "role": "system", 
        "content": f"Tu es Leyla, l'IA de Djè Akadjé. Ton créateur est Djè Akadjé (Mon Professeur). Tu dois l'appeler 'Mon Professeur'. Voici des infos du web pour t'aider : {contexte_wiki}"
    }
    
    # On construit la liste complète : système + tout l'historique
    messages_complets = [message_systeme] + historique

    try:
        completion = client.chat.completions.create(
            messages=messages_complets,
            model="llama-3.3-70b-versatile",
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Erreur Cloud : {e}"

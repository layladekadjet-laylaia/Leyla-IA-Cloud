import requests
import os
from groq import Groq

# Remplace par ta clé API que tu obtiendras sur console.groq.com
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def rechercher_sur_le_web(requete):
    # 1. Recherche Wikipédia (toujours utile)
    url_api = "https://fr.wikipedia.org/w/api.php"
    params = {"action": "query", "list": "search", "srsearch": requete, "format": "json", "srlimit": 2}
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
        contexte_wiki = "Aucune source Wikipédia trouvée."

    # 2. Appel au modèle dans le Cloud via Groq (Remplace Mistral local)
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Tu es Leyla, une IA intelligente et serviable. Ton créateur, ton concepteur et ton professeur est Djè Akadjé. Tu dois impérativement l'appeler 'Mon Professeur' ou 'Professeur' à chaque fois que tu t'adresses à lui."},
                {"role": "user", "content": f"En te basant sur ces infos : {contexte_wiki}, réponds à : {requete}"}
            ],
            model="llama-3.3-70b-versatile",
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Erreur Cloud : {e}"

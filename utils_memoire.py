from groq import Groq
import os

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def generer_resume(historique):
    # On ne prend que les messages importants (exclure le système)
    texte_a_resumer = "\n".join([f"{msg['role']}: {msg['content']}" for msg in historique[-10:]])
    
    prompt_resume = f"Voici les derniers échanges d'une conversation. Fais un résumé concis des points clés, des projets et des préférences de l'utilisateur Djè Akadjé pour garder en mémoire : {texte_a_resumer}"
    
    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt_resume}],
        model="llama-3.3-70b-versatile",
    )
    return completion.choices[0].message.content

from groq import Groq
import os
import db_manager # Importez db_manager pour récupérer le nom

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def generer_resume(historique):
    # Récupérer le nom dynamique de l'utilisateur
    user_name = db_manager.get_user_name() or "Utilisateur"
    
    # On ne prend que les messages importants (exclure le système)
    texte_a_resumer = "\n".join([f"{msg['role']}: {msg['content']}" for msg in historique[-10:]])
    
    # Utilisation du nom dynamique dans le prompt
    prompt_resume = f"Voici les derniers échanges d'une conversation. Fais un résumé concis des points clés, des projets et des préférences de l'utilisateur {user_name} pour garder en mémoire : {texte_a_resumer}"
    
    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt_resume}],
        model="openai/gpt-oss-20b",
    )
    return completion.choices[0].message.content

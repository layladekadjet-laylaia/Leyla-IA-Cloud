import os
import base64
import re
import io
from PIL import Image
from groq import Groq
from duckduckgo_search import DDGS

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def image_to_base64(image_file):
    """Convertit et compresse l'image pour optimiser la taille de la requête"""
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
            
        image = Image.open(io.BytesIO(data))
        
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
            
        image.thumbnail((512, 512))
        
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=75)
        
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception:
        return None

def nettoyer_reponse(texte):
    """Nettoie les balises, supprime les répétitions et filtre l'anglais résiduel"""
    if not texte:
        return ""
    
    # 1. Supprime les balises de réflexion
    texte = re.sub(r'<think>.*?</think>', '', texte, flags=re.DOTALL).strip()
    
    # 2. Nettoyage de sécurité contre les mots en anglais courantes
    mots_anglais_interdits = [
        r'\bthe\b', r'\band\b', r'\byou\b', r'\bcan\b', r'\bimage\b', 
        r'\bvision\b', r'\bmodel\b', r'\bplease\b', r'\bnotice\b'
    ]
    for mot in mots_anglais_interdits:
        texte = re.sub(mot, '', texte, flags=re.IGNORECASE)

    # 3. Supprime les lignes répétées en boucle
    lignes = texte.split('\n')
    lignes_propres = []
    derniere_ligne = ""
    
    for ligne in lignes:
        ligne_str = ligne.strip()
        if ligne_str and ligne_str == derniere_ligne:
            continue
        lignes_propres.append(ligne)
        if ligne_str:
            derniere_ligne = ligne_str
            
    return '\n'.join(lignes_propres).strip()

def rechercher_sur_le_web(historique, image_file=None):
    historique_reduit = historique[-3:] if len(historique) > 3 else historique
    
    derniere_requete = historique_reduit[-1]["content"] if historique_reduit else ""
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
        "content": (
            f"Tu es Leyla, l'intelligence artificielle exclusive de Djè Akadjé. Appelle-le impérativement 'Mon Professeur'. "
            f"LANGUE OBLIGATOIRE : Rédige l'intégralité de ta réponse en français courant. L'utilisation de l'anglais est formellement interdite. "
            f"RÈGLE DE VOIX : N'utilise aucun symbole de mise en forme (pas d'astérisques, pas de tirets, pas de dièses, pas de puces). "
            f"Écris uniquement des phrases en texte brut fluide, naturel et sans répétition. "
            f"Voici des infos web : {contexte_web}"
        )
    }
    
    messages_formates = [message_systeme]
    img_b64 = image_to_base64(image_file) if image_file else None
    
    for i, msg in enumerate(historique_reduit):
        if i == len(historique_reduit) - 1 and img_b64:
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
            model="qwen/qwen3.6-27b",
            messages=messages_formates,
            max_tokens=1024,
            temperature=0.2
        )
        reponse_brute = completion.choices[0].message.content
        return nettoyer_reponse(reponse_brute)
        
    except Exception as e:
        return f"Erreur IA : {str(e)}"

import os
import re
from PIL import Image
from google import genai
from google.genai import types
from duckduckgo_search import DDGS

# Initialisation du client Google GenAI avec la clé d'environnement
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def nettoyer_reponse(texte):
    """Nettoie les balises, supprime les répétitions et filtre l'anglais résiduel"""
    if not texte:
        return ""
    
    # 1. Supprime les balises de réflexion
    texte = re.sub(r'<think>.*?</think>', '', texte, flags=re.DOTALL).strip()
    
    # 2. Nettoyage de sécurité contre les mots en anglais courants
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
        if ligne_str and ligne_str == dernière_ligne:
            continue
        lignes_propres.append(ligne)
        if ligne_str:
            dernière_ligne = ligne_str
            
    return '\n'.join(lignes_propres).strip()

def rechercher_sur_le_web(historique, image_file=None):
    # Réduction de l'historique pour garder le contexte récent
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

    # Consignes strictes pour Leyla
    consignes_systeme = (
        f"Tu es Leyla, l'intelligence artificielle exclusive de Djè Akadjé. Appelle-le impérativement 'Mon Professeur'. "
        f"LANGUE OBLIGATOIRE : Rédige l'intégralité de ta réponse en français courant. L'utilisation de l'anglais est formellement interdite. "
        f"RÈGLE DE VOIX : N'utilise aucun symbole de mise en forme (pas d'astérisques, pas de tirets, pas de dièses, pas de puces). "
        f"Écris uniquement des phrases en texte brut fluide, naturel et sans répétition. "
        f"Informations web contextuelles : {contexte_web}"
    )

    # Préparation du contenu pour le nouveau SDK Gemini
    contenus_prompt = []

    # Si une image est fournie, on l'ouvre proprement avec PIL et on l'ajoute
    if image_file is not None:
        try:
            image_file.seek(0) if hasattr(image_file, "seek") else None
            pil_img = Image.open(image_file)
            contenus_prompt.append(pil_img)
        except Exception:
            pass

    # Reconstruction de l'historique textuel pour le prompt de fin
    historique_texte = ""
    for msg in historique_reduit:
        role_label = "Utilisateur" if msg["role"] == "user" else "Leyla"
        # Nettoyage des balises d'images textuelles éventuelles dans l'historique
        texte_propre_msg = re.sub(r'\[Image transmise\]', '', msg["content"]).strip()
        historique_texte += f"{role_label} : {texte_propre_msg}\n"

    contenus_prompt.append(historique_texte)

    try:
        # Appel direct au modèle Gemini via le client officiel Google GenAI
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contenus_prompt,
            config=types.GenerateContentConfig(
                system_instruction=consignes_systeme,
                temperature=0.3,
                max_output_tokens=1024,
            )
        )
        
        reponse_brute = response.text if response and response.text else "Je n'ai pas pu générer de réponse."
        return nettoyer_reponse(reponse_brute)
        
    except Exception as e:
        return f"Erreur IA (Gemini) : {str(e)}"

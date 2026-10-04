import os
import time
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import pygetwindow as gw
import sounddevice as sd
import scipy.io.wavfile as wav

import secretaire_leyla

# --- CONFIGURATION EMAIL ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_EXPEDITEUR = os.getenv("EMAIL_EXPEDITEUR", "votre.email@gmail.com")
MOT_DE_PASSE_EMAIL = os.getenv("EMAIL_PASSWORD", "votre_mot_de_passe_app")

# Fenêtres d'applications de réunion à surveiller
APPLIS_REUNION = ["zoom", "meet", "teams", "webex", "skype"]

def detecter_reunion_active() -> tuple[bool, str]:
    """Vérifie si une application de réunion en ligne est ouverte sur l'écran."""
    fenetres = gw.getAllTitles()
    for fenetre in fenetres:
        titre_lower = fenetre.lower()
        for app in APPLIS_REUNION:
            if app in titre_lower and len(titre_lower.strip()) > 0:
                return True, fenetre
    return False, ""

def enregistrer_audio_reunion(fichier_sortie: str, stop_condition_func, Freq_echantillon: int = 44100):
    """Enregistre le flux sonore en continu jusqu'à la fermeture de la réunion."""
    import numpy as np

    donnees_audio = []
    
    def callback(indata, frames, time_info, status):
        donnees_audio.append(indata.copy())

    # Démarre la capture audio sur les haut-parleurs/micro
    with sd.InputStream(samplerate=Freq_echantillon, channels=2, callback=callback):
        while not stop_condition_func():
            time.sleep(1)

    if donnees_audio:
        enregistrement = np.concatenate(donnees_audio, axis=0)
        wav.write(fichier_sortie, Freq_echantillon, enregistrement)

def envoyer_email_compte_rendu(destinataires: list[str], sujet: str, corps_markdown: str, chemin_fichier_attache: str = None):
    """Envoie le compte-rendu par e-mail aux participants."""
    if not EMAIL_EXPEDITEUR or not MOT_DE_PASSE_EMAIL:
        print("Configuration SMTP absente. Impossible d'envoyer les e-mails.")
        return False

    msg = MIMEMultipart()
    msg['From'] = f"Leyla - Secrétariat <{EMAIL_EXPEDITEUR}>"
    msg['To'] = ", ".join(destinataires)
    msg['Subject'] = sujet

    # Corps du message en texte/Markdown
    msg.attach(MIMEText(corps_markdown, 'plain', 'utf-8'))

    # Pièce jointe si présent
    if chemin_fichier_attache and os.path.exists(chemin_fichier_attache):
        with open(chemin_fichier_attache, "rb") as f:
            partie = MIMEBase('application', 'octet-stream')
            partie.set_payload(f.read())
            encoders.encode_base64(partie)
            partie.add_header('Content-Disposition', f'attachment; filename={os.path.basename(chemin_fichier_attache)}')
            msg.attach(partie)

    try:
        serveur = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        serveur.starttls()
        serveur.login(EMAIL_EXPEDITEUR, MOT_DE_PASSE_EMAIL)
        serveur.sendmail(EMAIL_EXPEDITEUR, destinataires, msg.as_string())
        serveur.quit()
        print(f"✅ Compte-rendu envoyé avec succès à : {', '.join(destinataires)}")
        return True
    except Exception as e:
        print(f"Erreur d'envoi d'e-mail : {str(e)}")
        return False

def extraire_emails_du_texte(texte: str) -> list[str]:
    """Extrait automatiquement toutes les adresses email détectées dans la synthèse ou la liste des participants."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return list(set(re.findall(pattern, texte)))

def surveiller_et_assister_reunions(emails_participants_defaut: list[str] = None):
    """Boucle autonome d'arrière-plan qui assiste aux réunions et distribue le compte-rendu."""
    print("🤖 Leyla : Service de secrétariat automatique activé en arrière-plan...")
    
    while True:
        reunion_en_cours, titre_fenetre = detecter_reunion_active()
        
        if reunion_en_cours:
            print(f"\n🎙️ Réunion détectée : '{titre_fenetre}'. Leyla commence la prise de notes...")
            
            horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
            fichier_audio_temp = f"temp_reunion_{horodatage}.wav"
            
            # Condition pour vérifier si la fenêtre de réunion est toujours ouverte
            def reunion_est_terminee():
                active, _ = detecter_reunion_active()
                return not active

            # Enregistrement passif pendant toute la durée
            enregistrer_audio_reunion(fichier_audio_temp, stop_condition_func=reunion_est_terminee)
            
            print("🏁 Réunion terminée ! Leyla rédige le compte-rendu de direction...")
            
            # Génération du rapport via le module secretaire_leyla
            compte_rendu = secretaire_leyla.generer_compte_rendu_reunion(
                chemin_fichier_media=fichier_audio_temp,
                titre_reunion=titre_fenetre,
                dossier_sortie="Compte_Rendus_Reunions"
            )
            
            # Identification des destinataires (extraits du rapport ou liste par défaut)
            emails = extraire_emails_du_texte(compte_rendu)
            if emails_participants_defaut:
                emails = list(set(emails + emails_participants_defaut))
                
            if emails:
                print(f"📧 Envoi automatique du rapport aux participants : {emails}")
                envoyer_email_compte_rendu(
                    destinataires=emails,
                    sujet=f"Compte-Rendu de Réunion : {titre_fenetre}",
                    corps_markdown=compte_rendu
                )
            else:
                print("⚠️ Aucune adresse e-mail trouvée pour l'envoi automatique.")
                
            # Nettoyage du fichier audio temporaire
            if os.path.exists(fichier_audio_temp):
                os.remove(fichier_audio_temp)
                
        time.sleep(5) # Vérification toutes les 5 secondes

if __name__ == "__main__":
    # Lancement du service
    surveiller_et_assister_reunions()

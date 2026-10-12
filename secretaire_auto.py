import os
import re
import smtplib
import time
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import numpy as np
import pygetwindow as gw
import scipy.io.wavfile as wav
import sounddevice as sd

import secretaire_leyla

# --- CONFIGURATION EMAIL DYNAMIQUE ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Titres d'applications de réunion à surveiller
APPLIS_REUNION = ["zoom", "meet", "teams", "webex", "skype"]


def obtenir_identifiants_email() -> tuple[str, str]:
    """Récupère l'e-mail et le mot de passe depuis l'environnement ou Streamlit Secrets."""
    expediteur = os.getenv("EMAIL_EXPEDITEUR", "")
    mdp = os.getenv("EMAIL_PASSWORD", "")

    if not expediteur or not mdp:
        try:
            import streamlit as st

            expediteur = expediteur or st.secrets.get("EMAIL_EXPEDITEUR", "")
            mdp = mdp or st.secrets.get("EMAIL_PASSWORD", "")
        except Exception:
            pass

    return expediteur, mdp


def detecter_reunion_active() -> tuple[bool, str]:
    """Vérifie si une fenêtre de réunion est active à l'écran."""
    try:
        fenetres = gw.getAllTitles()
        for fenetre in fenetres:
            titre_lower = fenetre.lower()
            for app in APPLIS_REUNION:
                if app in titre_lower and len(titre_lower.strip()) > 0:
                    return True, fenetre
    except Exception as e:
        print(f"Erreur détection fenêtres : {e}")
    return False, ""


def enregistrer_audio_reunion(
    fichier_sortie: str, stop_condition_func, freq_echantillon: int = 44100
):
    """Enregistre le flux sonore (Microphone + Haut-parleurs si disponible) jusqu'à la fin de la réunion."""
    donnees_audio = []

    def callback(indata, frames, time_info, status):
        if status:
            print(f"Statut audio : {status}")
        donnees_audio.append(indata.copy())

    try:
        # Tente la capture audio standard
        with sd.InputStream(
            samplerate=freq_echantillon, channels=2, callback=callback
        ):
            while not stop_condition_func():
                time.sleep(1)
    except Exception as err:
        print(f"⚠️ Avertissement capture audio : {err}")

    if donnees_audio:
        enregistrement = np.concatenate(donnees_audio, axis=0)
        wav.write(fichier_sortie, freq_echantillon, enregistrement)
        print(f"🎙️ Audio de réunion sauvegardé : {fichier_sortie}")


def envoyer_email_compte_rendu(
    destinataires: list[str],
    sujet: str,
    corps_markdown: str,
    chemin_fichier_attache: str = None,
) -> bool:
    """Envoie le compte-rendu aux participants via SMTP."""
    email_expediteur, mdp_email = obtenir_identifiants_email()

    if not email_expediteur or not mdp_email:
        print(
            "❌ Configuration SMTP manquante (EMAIL_EXPEDITEUR / EMAIL_PASSWORD non définis)."
        )
        return False

    msg = MIMEMultipart()
    msg["From"] = f"Leyla - Secrétariat <{email_expediteur}>"
    msg["To"] = ", ".join(destinataires)
    msg["Subject"] = sujet

    msg.attach(MIMEText(corps_markdown, "plain", "utf-8"))

    if chemin_fichier_attache and os.path.exists(chemin_fichier_attache):
        with open(chemin_fichier_attache, "rb") as f:
            partie = MIMEBase("application", "octet-stream")
            partie.set_payload(f.read())
            encoders.encode_base64(partie)
            partie.add_header(
                "Content-Disposition",
                f'attachment; filename="{os.path.basename(chemin_fichier_attache)}"',
            )
            msg.attach(partie)

    try:
        serveur = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        serveur.starttls()
        serveur.login(email_expediteur, mdp_email)
        serveur.sendmail(email_expediteur, destinataires, msg.as_string())
        serveur.quit()
        print(
            f"✅ Compte-rendu transmis avec succès à : {', '.join(destinataires)}"
        )
        return True
    except Exception as e:
        print(f"❌ Échec envoi e-mail : {str(e)}")
        return False


def extraire_emails_du_texte(texte: str) -> list[str]:
    """Extrait les adresses e-mail présentes dans le texte."""
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return list(set(re.findall(pattern, texte)))


def surveiller_et_assister_reunions(
    emails_participants_defaut: list[str] = None,
):
    """Service d'arrière-plan autonome qui capture les réunions et génère les comptes-rendus."""
    print(
        "🤖 Service Secrétariat Leyla activé. Surveillance des réunions en cours..."
    )

    while True:
        reunion_en_cours, titre_fenetre = detecter_reunion_active()

        if reunion_en_cours:
            print(
                f"\n🎙️ Réunion détectée : '{titre_fenetre}'. Leyla démarre la prise de note passive..."
            )

            horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
            fichier_audio_temp = f"temp_reunion_{horodatage}.wav"

            def reunion_est_terminee():
                active, _ = detecter_reunion_active()
                return not active

            try:
                # Capture audio autonome
                enregistrer_audio_reunion(
                    fichier_audio_temp,
                    stop_condition_func=reunion_est_terminee,
                )

                print("🏁 Réunion terminée. Rédaction du compte-rendu...")

                # Génération du rapport structuré via secretaire_leyla
                compte_rendu = (
                    secretaire_leyla.generer_compte_rendu_reunion(
                        chemin_fichier_media=fichier_audio_temp,
                        titre_reunion=titre_fenetre,
                        dossier_sortie="Compte_Rendus_Reunions",
                    )
                )

                # Identification des destinataires
                emails = extraire_emails_du_texte(compte_rendu)
                if emails_participants_defaut:
                    emails = list(set(emails + emails_participants_defaut))

                if emails:
                    print(f"📧 Distribution automatique à : {emails}")
                    envoyer_email_compte_rendu(
                        destinataires=emails,
                        sujet=f"Compte-Rendu : {titre_fenetre}",
                        corps_markdown=compte_rendu,
                    )
                else:
                    print(
                        "⚠️ Aucun destinataire e-mail identifié pour ce compte-rendu."
                    )

            except Exception as e:
                print(
                    f"❌ Erreur lors du traitement de la réunion : {str(e)}"
                )

            finally:
                # Nettoyage garanti du fichier temporaire
                if os.path.exists(fichier_audio_temp):
                    os.remove(fichier_audio_temp)

        time.sleep(5)


if __name__ == "__main__":
    surveiller_et_assister_reunions()

import time
import speech_recognition as sr

def ecouter_et_detecter():
    """Détection vocale adaptée aux contraintes Android."""
    recognizer = sr.Recognizer()
    
    # Ajustement de la sensibilité pour mobile
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True

    print("🎧 Leyla est en veille sur votre smartphone...")
    
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        
        while True:
            try:
                print("👂 Écoute en cours...")
                # Capture de courtes séquences
                audio = recognizer.listen(source, timeout=None, phrase_time_limit=4)
                
                # Reconnaissance via l'API Google
                texte = recognizer.recognize_google(audio, language="fr-FR").lower()
                print(f"Entendu : {texte}")
                
                # Détection du mot-clé "leyla"
                if "leyla" in texte:
                    print("\n✨ Mot-clé 'Leyla' détecté !")
                    
                    # Extraire la commande si elle est dans la même phrase (ex: "Leyla donne-moi la météo")
                    commande = texte.replace("leyla", "").strip()
                    
                    if not commande:
                        print("🎤 Dites votre commande, Mon Professeur...")
                        audio_commande = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                        commande = recognizer.recognize_google(audio_commande, language="fr-FR")
                    
                    print(f"🚀 Commande transmise à Leyla : '{commande}'")
                    
            except sr.UnknownValueError:
                # Bruit de fond non compris, on continue d'écouter
                continue
            except sr.RequestError as e:
                print(f"⚠️ Erreur réseau : {e}")
                time.sleep(2)
            except KeyboardInterrupt:
                print("\n🛑 Arrêt de l'écoute.")
                break

if __name__ == "__main__":
    ecouter_et_detecter()

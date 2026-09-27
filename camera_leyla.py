import cv2
import time
from vision_leyla import analyser_image

def capturer_et_analyser_camera_externe(rtsp_url: str) -> str:
    """
    Se connecte à une caméra IP (via RTSP ou HTTP),
    capture une image en direct et la transmet au module de vision de Leyla.
    """
    # Ouverture du flux vidéo réseau
    cap = cv2.VideoCapture(rtsp_url)
    
    if not cap.isOpened():
        erreur_msg = "❌ Impossible de se connecter à la caméra distante. Vérifiez l'adresse ou le réseau."
        print(erreur_msg)
        return erreur_msg

    print("👁️ Connexion au flux vidéo réussie. Capture de l'image...")
    
    # Capture une image du flux en direct
    ret, frame = cap.read()
    analyse_resultat = ""
    
    if ret:
        fichier_temp = "temp_camera_frame.jpg"
        # Sauvegarde temporaire de l'image
        cv2.imwrite(fichier_temp, frame)
        
        # Envoi direct à la vision de Leyla (Gemini 2.5 Flash)
        print("🧠 Transmis au cerveau visuel de Leyla...")
        analyse_resultat = analyser_image(
            fichier_temp, 
            "Analyse tout ce que tu vois sur ce flux caméra en détail, Mon Professeur."
        )
        print(f"\n📊 Analyse de Leyla :\n{analyse_resultat}")
    else:
        analyse_resultat = "⚠️ Échec de la capture d'image depuis le flux vidéo."
        print(analyse_resultat)
        
    cap.release()
    return analyse_resultat


if __name__ == "__main__":
    # Test local avec une caméra de démonstration ou votre caméra IP
    # Exemple d'adresse RTSP : "rtsp://admin:12345@192.168.1.50:554/stream1"
    URL_CAMERA_TEST = "rtsp://127.0.0.1:8554/live"
    capturer_et_analyser_camera_externe(URL_CAMERA_TEST)

import asyncio
import json
import threading
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

app = FastAPI(title="Leyla Multi-Device Hub")

# Registre des appareils connectés
appareils_connectes: Dict[str, WebSocket] = {}

class CommandeAppareil(BaseModel):
    appareil_cible: str
    action: str
    parametres: dict = {}

@app.get("/")
def status_hub():
    return {
        "statut": "Actif",
        "systeme": "Leyla Core Hub",
        "appareils_en_ligne": list(appareils_connectes.keys()),
    }

@app.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    await websocket.accept()
    appareils_connectes[device_id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await websocket.send_text(
                json.dumps({"status": "received", "from": device_id, "data": message})
            )
    except WebSocketDisconnect:
        del appareils_connectes[device_id]

async def envoyer_ordre_appareil(appareil_cible: str, action: str, params: dict = None) -> bool:
    if params is None:
        params = {}
    if appareil_cible in appareils_connectes:
        websocket = appareils_connectes[appareil_cible]
        ordre = {"action": action, "parametres": params}
        await websocket.send_text(json.dumps(ordre))
        return True
    return False

def demarrer_hub_arriere_plan():
    """Démarre le serveur FastAPI en arrière-plan sur le port 8000 uniquement."""
    import uvicorn
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

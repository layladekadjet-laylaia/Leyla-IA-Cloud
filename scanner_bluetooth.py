import asyncio
from bleak import BleakScanner


async def scanner_appareils():
    print("🔍 Recherche des appareils Bluetooth à proximité...")

    # Scan pendant 5 secondes
    devices = await BleakScanner.discover(timeout=5.0)

    if not devices:
        print("❌ Aucun appareil Bluetooth détecté.")
        return

    print(f"\n✅ {len(devices)} appareil(s) trouvé(s) :\n")
    for device in devices:
        nom = device.name if device.name else "Appareil inconnu"
        adresse = device.address
        rssi = device.rssi  # Plus le nombre est proche de 0, plus l'appareil est près
        print(f"📱 Nom : {nom} | Adresse : {adresse} | Signal (RSSI) : {rssi} dBm")


if __name__ == "__main__":
    asyncio.run(scanner_appareils())

# ==============================
# Imports
# ==============================

import time
import logging
#from pymodbus.client.sync import ModbusTcpClient
from pymodbus.client import ModbusTcpClient

# ==============================
# Configuration
# ==============================

# Anzahl Register pro Anlage (muss identisch zum Writer sein!)
REGISTER_STRIDE = 40

# Abfrageintervall in Sekunden
POLL_INTERVAL = 5

# Liste aller PV-Server (Raspberry Pis), die abgefragt werden sollen
DEVICES = [
    {
        "name": "PV1",
        "ip": "192.168.0.172",
        "port": 1502,
        "plants": 3,
    },
    {
        "name": "PV2",
        "ip": "192.168.0.195",
        "port": 1502,
        "plants": 3,
    },
]

# ==============================
# Decode helper
# ==============================

def decode_u32(high, low, scale=1):
    """
    Wandelt zwei 16-bit Modbus-Register in einen Float-Wert zurück.

    Vorgehen:
    - High-Word und Low-Word zu 32-bit Integer zusammensetzen
    - Skalierung rückgängig machen

    Beispiel:
    high=0x0000, low=2305, scale=10 → 230.5
    """
    return ((high << 16) | low) / scale


# ==============================
# Read one plant
# ==============================

def read_plant(client, plant_index):
    """
    Liest die Daten einer einzelnen PV-Anlage aus dem Modbus-Registerbereich.

    Parameter:
    - client: Modbus TCP Client
    - plant_index: Index der Anlage (0, 1, 2, ...)

    Rückgabe:
    - Dictionary mit allen Messwerten
    """

    # Startadresse berechnen (jede Anlage hat eigenen Block)
    base = plant_index * REGISTER_STRIDE

    # Register lesen
    result = client.read_holding_registers(base, REGISTER_STRIDE)

    # Fehler prüfen
    if result.isError():
        logging.error("Modbus read error for plant %s", plant_index + 1)
        return None

    regs = result.registers

    # Hilfsfunktion zum einfachen Zugriff auf 32-bit Werte
    def u32(i, scale=1):
        return decode_u32(regs[i], regs[i + 1], scale)

    # Alle Werte aus dem Registerbereich extrahieren
    return {
        "dc_voltage": u32(0, 10),
        "dc_current": u32(2, 100),
        "dc_power": u32(4, 1),
        "ac_voltage": u32(6, 10),
        "ac_current": u32(8, 100),
        "ac_power": u32(10, 1),
        "energy_kwh": u32(12, 100),
        "irradiance": u32(14, 1),
        "module_temp": u32(16, 10),
        "ambient_temp": u32(18, 10),
        "wind_speed": u32(20, 10),
        "status": int(u32(22, 1)),
    }


# ==============================
# Read full device (FIXED)
# ==============================

def read_device(device):
    """
    Verbindet sich zu einem Raspberry Pi und liest alle PV-Anlagen aus.

    Parameter:
    - device: Dictionary aus DEVICES
    """

    # Modbus TCP Verbindung aufbauen
    client = ModbusTcpClient(device["ip"], port=device["port"], timeout=3)

    # Verbindungsversuch
    if not client.connect():
        logging.error("Could not connect to %s (%s)", device["name"], device["ip"])
        return []

    results = []   # IMPORTANT: never return None

    try:
        # Überschrift für bessere Übersicht
        print(f"\n===== {device['name']} ({device['ip']}) =====")

        # Alle Anlagen dieses Geräts durchlaufen
        for plant_index in range(device["plants"]):
            data = read_plant(client, plant_index)

            # Nur ausgeben, wenn Daten erfolgreich gelesen wurden
            if data:
                results.append({
                    "source": device["name"],
                    "plant_id": plant_index + 1,
                    "data": data
                })

    except Exception as e:
        # Allgemeiner Fehler (z. B. Verbindungsabbruch)
        logging.error("Error reading %s: %s", device["name"], e)

    finally:
        # Verbindung immer schließen
        client.close()

    return results


# ==============================
# Optional test mode (standalone)
# ==============================

def run_gateway():
    """
    Endlosschleife:
    - fragt alle Geräte zyklisch ab
    - wartet zwischen den Zyklen
    """

    while True:
        # Alle Geräte nacheinander abfragen
        for device in DEVICES:
            data = read_device(device)

            if not data:
                logging.warning("No data from %s", device["name"])
                continue

            print(f"\n===== {device['name']} =====")

            for plant in data:
                d = plant["data"]

                print(
                    f"Plant {plant['plant_id']:02d} | "
                    f"DC={d['dc_power']:.1f} W | "
                    f"AC={d['ac_power']:.1f} W | "
                    f"Irr={d['irradiance']:.1f} | "
                    f"Temp={d['ambient_temp']:.1f} °C | "
                    f"Wind={d['wind_speed']:.1f} m/s | "
                    f"Status={d['status']}"
                )

        print("-" * 80)

        # Pause bis zur nächsten Abfrage
        time.sleep(POLL_INTERVAL)


# ==============================
# Programmstart
# ==============================

if __name__ == "__main__":
    # Logging konfigurieren
    logging.basicConfig(level=logging.INFO)

    # Gateway starten
    run_gateway()
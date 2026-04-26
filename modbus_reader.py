# ==============================
# Imports
# ==============================

import time
import logging
from pymodbus.client.sync import ModbusTcpClient

# ==============================
# Grundkonfiguration
# ==============================

# Anzahl Register pro Anlage (muss identisch zum Writer sein!)
REGISTER_STRIDE = 40

# Abfrageintervall in Sekunden
POLL_INTERVAL = 5

# Liste aller PV-Server (Raspberry Pis), die abgefragt werden sollen
DEVICES = [
    {
        "name": "PV1",               # Name der Anlage / Quelle
        "ip": "192.168.0.172",      # IP-Adresse des Raspberry Pi
        "port": 1502,               # Modbus TCP Port
        "plants": 3,                # Anzahl PV-Anlagen auf diesem Gerät
    },
    {
        "name": "PV2",
        "ip": "192.168.0.195",
        "port": 1502,
        "plants": 3,
    },
]

# ==============================
# Hilfsfunktion: 32-bit Wert dekodieren
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
# Eine PV-Anlage auslesen
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
# Ein Gerät (Raspberry) auslesen
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
        return

    try:
        # Überschrift für bessere Übersicht
        print(f"\n===== {device['name']} ({device['ip']}) =====")

        # Alle Anlagen dieses Geräts durchlaufen
        for plant_index in range(device["plants"]):
            data = read_plant(client, plant_index)

            # Nur ausgeben, wenn Daten erfolgreich gelesen wurden
            if data:
                print(
                    f"Plant {plant_index + 1:02d} | "
                    f"DC={data['dc_power']:.1f} W | "
                    f"AC={data['ac_power']:.1f} W | "
                    f"Irr={data['irradiance']:.1f} W/m² | "
                    f"Temp={data['ambient_temp']:.1f} °C | "
                    f"Wind={data['wind_speed']:.1f} m/s | "
                    f"Status={data['status']}"
                )

    except Exception as e:
        # Allgemeiner Fehler (z. B. Verbindungsabbruch)
        logging.error("Error reading %s: %s", device["name"], e)

    finally:
        # Verbindung immer schließen
        client.close()


# ==============================
# Hauptloop (Edge Gateway)
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
            read_device(device)

        # Trenner für bessere Lesbarkeit
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
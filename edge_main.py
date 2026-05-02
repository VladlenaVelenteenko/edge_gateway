# benötigt für die Pause zwischen den Polling-Zyklen
import time

# benötigt für Log-Ausgaben im Terminal
import logging

# liest die Modbus-Daten von PV1 / PV2 aus
from modbus_reader import read_server

# baut aus den gelesenen Daten Payloads und Summaries
from data_processor import build_payload, build_summary

# kümmert sich um die MQTT-Verbindung und das Senden der Nachrichten
from mqtt_publisher import MqttPublisher


# Liste der Field Devices, von denen der Edge Daten lesen soll
FIELD_DEVICES = [
    {
        "name": "pv1",              # Name des ersten PV-Simulators
        "ip": "100.96.140.85",      # IP-Adresse von PV1
        "port": 1502,               # Modbus TCP Port
        "plants": 3                 # Anzahl der simulierten Anlagen auf PV1
    },
    {
        "name": "pv2",              # Name des zweiten PV-Simulators
        "ip": "100.97.52.86",       # IP-Adresse von PV2
        "port": 1502,               # Modbus TCP Port
        "plants": 3                 # Anzahl der simulierten Anlagen auf PV2
    }
]

# IP-Adresse des MQTT-Brokers / SCADA-Systems
MQTT_BROKER = "192.168.10.200"

# Standard-Port für MQTT
MQTT_PORT = 1883

# alle 5 Sekunden werden neue Daten von PV1 / PV2 gelesen
POLL_INTERVAL = 5

# Zwischenspeicher für Nachrichten, falls MQTT gerade nicht erreichbar ist
buffer = []


# versucht eine Nachricht per MQTT zu senden
# wenn das Senden fehlschlägt, wird die Nachricht im Buffer gespeichert
def publish_or_buffer(mqtt_client, topic, payload):
    success = mqtt_client.publish(topic, payload)

    if not success:
        buffer.append({
            "topic": topic,
            "payload": payload
        })
        logging.warning("Payload buffered for topic %s", topic)


# versucht alle gespeicherten Nachrichten aus dem Buffer erneut zu senden
def flush_buffer(mqtt_client):
    global buffer

    # wenn nichts im Buffer ist, gibt es nichts zu tun
    if not buffer:
        return

    # Nachrichten, die wieder nicht gesendet werden konnten, bleiben erhalten
    remaining = []

    for item in buffer:
        success = mqtt_client.publish(item["topic"], item["payload"])

        if not success:
            remaining.append(item)

    # Buffer wird durch die noch nicht gesendeten Nachrichten ersetzt
    buffer = remaining


# verarbeitet ein einzelnes Field Device, z. B. pv1 oder pv2
def process_device(device, mqtt_client):

    # Modbus-Daten vom jeweiligen PV-Simulator lesen
    raw_plants = read_server(device)

    # hier werden alle Payloads dieses Geräts gesammelt
    payloads = []

    for plant in raw_plants:

        # aus den Rohdaten wird ein sauberes Payload pro Anlage gebaut
        payload = build_payload(
            source=plant["source"],
            plant_id=plant["plant_id"],
            data=plant["data"]
        )

        # Payload zur Liste hinzufügen, damit später eine Summary berechnet werden kann
        payloads.append(payload)

        # MQTT-Topic für die einzelne Anlage
        # Beispiel: pv/pv1/plant/1
        topic = f"pv/{device['name']}/plant/{plant['plant_id']}"

        # Payload senden oder bei Fehler puffern
        publish_or_buffer(mqtt_client, topic, payload)

    # aus allen Payloads dieses Geräts wird eine Zusammenfassung erstellt
    summary = build_summary(device["name"], payloads)

    # MQTT-Topic für die Summary
    # Beispiel: pv/pv1/summary
    summary_topic = f"pv/{device['name']}/summary"

    # Summary senden oder bei Fehler puffern
    publish_or_buffer(mqtt_client, summary_topic, summary)


# Startpunkt des Edge Gateways
def main():

    # Logging konfigurieren, damit im Terminal nachvollziehbar ist, was passiert
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    # MQTT-Client erstellen
    mqtt_client = MqttPublisher(MQTT_BROKER, MQTT_PORT)

    # Verbindung zum MQTT-Broker herstellen
    mqtt_client.connect()

    try:
        # Endlosschleife: Edge Gateway läuft dauerhaft
        while True:

            # jedes Field Device nacheinander verarbeiten
            for device in FIELD_DEVICES:
                process_device(device, mqtt_client)

            # falls alte Nachrichten im Buffer liegen, erneut senden
            flush_buffer(mqtt_client)

            # Log-Ausgabe nach jedem vollständigen Polling-Zyklus
            logging.info("Polling cycle finished. Buffered messages: %d", len(buffer))

            # warten bis zum nächsten Polling-Zyklus
            time.sleep(POLL_INTERVAL)

    # sauberes Beenden mit CTRL + C
    except KeyboardInterrupt:
        logging.info("Stopping Edge Gateway...")

    # MQTT-Verbindung beim Beenden schließen
    finally:
        mqtt_client.disconnect()


# sorgt dafür, dass main() nur gestartet wird,
# wenn diese Datei direkt ausgeführt wird
if __name__ == "__main__":
      main()
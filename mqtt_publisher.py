# wird verwendet, um Python-Daten (Dictionary) in JSON umzuwandeln
import json

# für Log-Ausgaben im Terminal
import logging

# MQTT-Bibliothek für die Kommunikation mit dem Broker
import paho.mqtt.client as mqtt


# Klasse für das Senden von Daten über MQTT
class MqttPublisher:

    # wird beim Erstellen des Objekts aufgerufen
    def __init__(self, broker_host, broker_port=1883, client_id="edge-gateway"):

        # speichert die Adresse des MQTT-Brokers
        self.broker_host = broker_host

        # speichert den Port (Standard: 1883)
        self.broker_port = broker_port

        # erstellt einen MQTT-Client mit einer eindeutigen ID
        self.client = mqtt.Client(client_id=client_id)

        # merkt sich, ob eine Verbindung besteht
        self.connected = False


    # baut die Verbindung zum MQTT-Broker auf
    def connect(self):
        try:
            # Verbindung herstellen
            self.client.connect(self.broker_host, self.broker_port)

            # startet eine Hintergrundschleife für MQTT (wichtig für Kommunikation)
            self.client.loop_start()

            # Verbindung als erfolgreich markieren
            self.connected = True

            # Log-Ausgabe
            logging.info("Connected to MQTT broker %s:%s", self.broker_host, self.broker_port)

        # falls etwas schiefgeht (z. B. falsche IP)
        except Exception as e:
            self.connected = False
            logging.error("MQTT connection failed: %s", e)


    # sendet eine Nachricht an ein bestimmtes Topic
    def publish(self, topic, payload):

        # wenn keine Verbindung besteht → nichts senden
        if not self.connected:
            logging.warning("MQTT not connected. Could not publish to %s", topic)
            return False

        try:
            # Payload (Python-Dictionary) wird in JSON umgewandelt
            message = json.dumps(payload)

            # Nachricht an das Topic senden
            result = self.client.publish(topic, message)

            # prüfen, ob das Senden erfolgreich war
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logging.error("MQTT publish failed for topic %s", topic)
                return False

            # Erfolg loggen
            logging.info("Published to %s", topic)
            return True

        # falls beim Senden ein Fehler passiert
        except Exception as e:
            logging.error("MQTT publish exception: %s", e)
            return False


    # beendet die Verbindung zum MQTT-Broker
    def disconnect():

        # stoppt die Hintergrundschleife
        self.client.loop_stop()

        # trennt die Verbindung
        self.client.disconnect(self)

        # merkt sich, dass keine Verbindung mehr besteht
        self.connected = False
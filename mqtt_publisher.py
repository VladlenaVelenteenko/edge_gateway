import json
import logging
import paho.mqtt.client as mqtt


class MqttPublisher:
    def __init__(self, broker_host, broker_port=1883, client_id="edge-gateway"):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = mqtt.Client(client_id=client_id)
        self.connected = False

    def connect(self):
        try:
            self.client.connect(self.broker_host, self.broker_port)
            self.client.loop_start()
            self.connected = True
            logging.info("Connected to MQTT broker %s:%s", self.broker_host, self.broker_port)
        except Exception as e:
            self.connected = False
            logging.error("MQTT connection failed: %s", e)

    def publish(self, topic, payload):
        if not self.connected:
            logging.warning("MQTT not connected. Could not publish to %s", topic)
            return False

        try:
            message = json.dumps(payload)
            result = self.client.publish(topic, message)

            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logging.error("MQTT publish failed for topic %s", topic)
                return False

            logging.info("Published to %s", topic)
            return True

        except Exception as e:
            logging.error("MQTT publish exception: %s", e)
            return False

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False
import time
import logging

from modbus_reader import read_server
from data_processor import build_payload, build_summary
from mqtt_publisher import MqttPublisher


FIELD_DEVICES = [
    {
        "name": "pv1",
        "ip": "100.96.140.85",
        "port": 1502,
        "plants": 3
    },
    {
        "name": "pv2",
        "ip": "100.97.52.86",
        "port": 1502,
        "plants": 3
    }
]

MQTT_BROKER = "192.168.10.200"
MQTT_PORT = 1883

POLL_INTERVAL = 5

buffer = []


def publish_or_buffer(mqtt_client, topic, payload):
    success = mqtt_client.publish(topic, payload)

    if not success:
        buffer.append({
            "topic": topic,
            "payload": payload
        })
        logging.warning("Payload buffered for topic %s", topic)


def flush_buffer(mqtt_client):
    global buffer

    if not buffer:
        return

    remaining = []

    for item in buffer:
        success = mqtt_client.publish(item["topic"], item["payload"])

        if not success:
            remaining.append(item)

    buffer = remaining


def process_device(device, mqtt_client):
    raw_plants = read_server(device)
    payloads = []

    for plant in raw_plants:
        payload = build_payload(
            source=plant["source"],
            plant_id=plant["plant_id"],
            data=plant["data"]
        )

        payloads.append(payload)

        topic = f"pv/{device['name']}/plant/{plant['plant_id']}"
        publish_or_buffer(mqtt_client, topic, payload)

    summary = build_summary(device["name"], payloads)
    summary_topic = f"pv/{device['name']}/summary"

    publish_or_buffer(mqtt_client, summary_topic, summary)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    mqtt_client = MqttPublisher(MQTT_BROKER, MQTT_PORT)
    mqtt_client.connect()

    try:
        while True:
            for device in FIELD_DEVICES:
                process_device(device, mqtt_client)

            flush_buffer(mqtt_client)

            logging.info("Polling cycle finished. Buffered messages: %d", len(buffer))
            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        logging.info("Stopping Edge Gateway...")

    finally:
        mqtt_client.disconnect()


if __name__ == "__main__":
    main()
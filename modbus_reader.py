# ==============================
# Imports
# ==============================

import time
import logging
from pymodbus.client.sync import ModbusTcpClient

# ==============================
# Configuration
# ==============================

REGISTER_STRIDE = 40
POLL_INTERVAL = 5

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
    return ((high << 16) | low) / scale


# ==============================
# Read one plant
# ==============================

def read_plant(client, plant_index):
    base = plant_index * REGISTER_STRIDE

    result = client.read_holding_registers(base, REGISTER_STRIDE)

    if result.isError():
        logging.error("Modbus read error for plant %s", plant_index + 1)
        return None

    regs = result.registers

    def u32(i, scale=1):
        return decode_u32(regs[i], regs[i + 1], scale)

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
    client = ModbusTcpClient(device["ip"], port=device["port"], timeout=3)

    if not client.connect():
        logging.error("Could not connect to %s (%s)", device["name"], device["ip"])
        return []

    results = []   # IMPORTANT: never return None

    try:
        for plant_index in range(device["plants"]):
            data = read_plant(client, plant_index)

            if data:
                results.append({
                    "source": device["name"],
                    "plant_id": plant_index + 1,
                    "data": data
                })

    except Exception as e:
        logging.error("Error reading %s: %s", device["name"], e)

    finally:
        client.close()

    return results


# ==============================
# Optional test mode (standalone)
# ==============================

def run_gateway():
    while True:
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
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_gateway()
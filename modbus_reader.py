import logging
from pymodbus.client import ModbusTcpClient

REGISTER_STRIDE = 40


def decode_u32(high, low, scale=1):
    value = (high << 16) | low
    return value / scale


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
        "status": regs[22],
    }


def read_server(device):
    client = ModbusTcpClient(device["ip"], port=device["port"])
    plant_data = []

    if not client.connect():
        logging.error("Could not connect to %s (%s)", device["name"], device["ip"])
        return []

    try:
        for plant_index in range(device["plants"]):
            data = read_plant(client, plant_index)

            if data is not None:
                plant_data.append({
                    "source": device["name"],
                    "plant_id": plant_index + 1,
                    "data": data
                })

    finally:
        client.close()

    return plant_data

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    device = {
        "name": "PV1",
        "ip": "192.168.10.101",
        "port": 1502,
        "plants": 3,
    }

    data = read_server(device)

    for d in data:
        print(d)
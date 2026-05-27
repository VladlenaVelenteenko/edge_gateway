from datetime import datetime, timezone


def current_timestamp():
    return datetime.now(timezone.utc).isoformat()


def validate_plant_data(data):
    errors = []

    numeric_fields = [
        "dc_voltage",
        "dc_current",
        "dc_power",
        "ac_voltage",
        "ac_current",
        "ac_power",
        "energy_kwh",
        "irradiance",
        "module_temp",
        "ambient_temp",
        "wind_speed",
    ]

    for field in numeric_fields:
        if field not in data:
            errors.append(f"Missing field: {field}")
        elif data[field] < 0:
            errors.append(f"Negative value in {field}: {data[field]}")

    if data.get("status") not in [1, 2]:
        errors.append(f"Invalid status: {data.get('status')}")

    if data.get("ac_power", 0) > data.get("dc_power", 0):
        errors.append("AC power is higher than DC power")

    return errors


def build_payload(source, plant_id, data):
    errors = validate_plant_data(data)

    return {
        "type": "plant",   # ✅ ADDED
        "source": source,
        "plant_id": plant_id,
        "timestamp": current_timestamp(),
        "valid": len(errors) == 0,
        "errors": errors,
        **data
    }


def build_summary(source, payloads):
    valid_payloads = [p for p in payloads if p["valid"]]

    if not valid_payloads:
        return {
            "type": "summary",   # ✅ ADDED
            "source": source,
            "timestamp": current_timestamp(),
            "plant_count": 0,
            "valid": False,
            "error": "No valid plant data available"
        }

    return {
        "type": "summary",   # ✅ ADDED
        "source": source,
        "timestamp": current_timestamp(),
        "plant_count": len(valid_payloads),
        "total_dc_power": sum(p["dc_power"] for p in valid_payloads),
        "total_ac_power": sum(p["ac_power"] for p in valid_payloads),
        "total_energy_kwh": sum(p["energy_kwh"] for p in valid_payloads),
        "avg_module_temp": sum(p["module_temp"] for p in valid_payloads) / len(valid_payloads),
        "avg_ambient_temp": sum(p["ambient_temp"] for p in valid_payloads) / len(valid_payloads),
        "avg_irradiance": sum(p["irradiance"] for p in valid_payloads) / len(valid_payloads),
        "fault_count": sum(1 for p in valid_payloads if p["status"] == 2),
        "valid": True
    }
# Import für Zeitstempel (Datum + Uhrzeit)
from datetime import datetime, timezone


# erzeugt die aktuelle Zeit in UTC im standardisierten ISO-Format
# Beispiel: 2026-04-26T13:30:00Z
def current_timestamp():
    return datetime.now(timezone.utc).isoformat()


# überprüft, ob die Messdaten einer PV-Anlage plausibel sind
def validate_plant_data(data):
    errors = []  # hier werden alle gefundenen Fehler gesammelt

    # alle Felder, die Zahlenwerte enthalten müssen
    numeric_fields = [
        "dc_voltage",     # Gleichspannung
        "dc_current",     # Gleichstrom
        "dc_power",       # Gleichleistung
        "ac_voltage",     # Wechselspannung
        "ac_current",     # Wechselstrom
        "ac_power",       # Wechselleistung
        "energy_kwh",     # erzeugte Energie
        "irradiance",     # Sonneneinstrahlung
        "module_temp",    # Modultemperatur
        "ambient_temp",   # Umgebungstemperatur
        "wind_speed",     # Windgeschwindigkeit
    ]

    # jedes Feld wird geprüft
    for field in numeric_fields:

        # wenn ein Feld fehlt → Fehler
        if field not in data:
            errors.append(f"Missing field: {field}")

        # wenn ein Wert negativ ist → physikalisch nicht sinnvoll
        elif data[field] < 0:
            errors.append(f"Negative value in {field}: {data[field]}")

    # Status prüfen (1 = OK, 2 = Fehler)
    if data.get("status") not in [1, 2]:
        errors.append(f"Invalid status: {data.get('status')}")

    # Plausibilitätscheck:
    # AC-Leistung darf nicht größer sein als DC-Leistung
    if data.get("ac_power", 0) > data.get("dc_power", 0):
        errors.append("AC power is higher than DC power")

    # alle gefundenen Fehler zurückgeben
    return errors


# erstellt ein Datenpaket (Payload) für eine einzelne PV-Anlage
def build_payload(source, plant_id, data):

    # zuerst werden die Daten überprüft
    errors = validate_plant_data(data)

    # fertiges Payload zusammenbauen
    return {
        "source": source,                 # z. B. pv1 oder pv2
        "plant_id": plant_id,             # welche Anlage
        "timestamp": current_timestamp(),# Zeitpunkt der Messung

        # True, wenn keine Fehler gefunden wurden
        "valid": len(errors) == 0,

        # Liste aller Fehler (leer wenn alles passt)
        "errors": errors,

        # alle Messwerte werden hier direkt übernommen
        **data
    }


# erstellt eine Zusammenfassung über mehrere Anlagen
def build_summary(source, payloads):

    # nur gültige Daten berücksichtigen
    valid_payloads = [p for p in payloads if p["valid"]]

    # wenn keine gültigen Daten vorhanden sind
    if not valid_payloads:
        return {
            "source": source,
            "timestamp": current_timestamp(),
            "plant_count": 0,
            "valid": False,
            "error": "No valid plant data available"
        }

    # Zusammenfassung berechnen
    return {
        "source": source,
        "timestamp": current_timestamp(),

        # Anzahl der gültigen Anlagen
        "plant_count": len(valid_payloads),

        # Gesamtleistung aller Anlagen
        "total_dc_power": sum(p["dc_power"] for p in valid_payloads),
        "total_ac_power": sum(p["ac_power"] for p in valid_payloads),

        # gesamte erzeugte Energie
        "total_energy_kwh": sum(p["energy_kwh"] for p in valid_payloads),

        # Durchschnittswerte
        "avg_module_temp": sum(p["module_temp"] for p in valid_payloads) / len(valid_payloads),
        "avg_ambient_temp": sum(p["ambient_temp"] for p in valid_payloads) / len(valid_payloads),
        "avg_irradiance": sum(p["irradiance"] for p in valid_payloads) / len(valid_payloads),

        # Anzahl der Anlagen mit Fehlerstatus
        "fault_count": sum(1 for p in valid_payloads if p["status"] == 2),

        # Summary ist gültig, wenn mindestens eine gültige Anlage vorhanden ist
        "valid": True
    }
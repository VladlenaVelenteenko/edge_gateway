
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "communication"
    / "communication_events.jsonl"
)


def record_event(device, start_address, register_count,
                 response_time_ms, success, timeout=False,
                 exception_code=None):

    event = {
        "event_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "observer": "edge",
        "destination_ip": device["ip"],
        "destination_port": device["port"],
        "function_code": 3,
        "start_address": start_address,
        "register_count": register_count,
        "response_time_ms": round(response_time_ms, 3),
        "success": success,
        "timeout": timeout,
        "exception_code": exception_code
    }

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with DATA_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event) + "\n")

    return event

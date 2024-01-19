import json
from datetime import datetime


def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")


def serialize_date_times(obj):
    serialized_results = json.dumps(obj, default=datetime_serializer)
    return json.loads(serialized_results)


def log(message):
    timestamp = datetime.utcnow().isoformat()
    log_entry = f"[{timestamp}]: {message}"
    print(log_entry.rstrip())


def proc_type_2_short(proc_type):
    if proc_type == 'SPEED_EVALUATION':
        return 'speed'
    elif proc_type == 'MTLCR_CALCULATION':
        return 'mtlcr'
    elif proc_type == 'TLIR_CALCULATION':
        return 'tlir'
    else:
        return

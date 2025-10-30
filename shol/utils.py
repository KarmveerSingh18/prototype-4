import os, yaml, time, json, datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "services.yaml"
LOG_PATH = BASE_DIR / "logs" / "events.log"

def load_services():
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f) or {}

def ts():
    return time.time()

def now_str():
    import datetime
    return datetime.datetime.fromtimestamp(ts()).strftime("%Y-%m-%d %H:%M:%S")

LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "events.log"


def log_event(event_type, details=""):
    """Logs an event with a timestamp and details into events.log"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {event_type}: {details}\n")

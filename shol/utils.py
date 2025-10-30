import os, yaml, time, json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "services.yaml"

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

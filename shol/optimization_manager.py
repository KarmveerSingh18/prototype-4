import json
import os
import time
import psutil
from collections import deque

WHITELIST_FILE = os.path.join(os.path.dirname(__file__), "whitelist.json")
OPTIMIZATION_LOG = deque(maxlen=10)  # Store last 10 optimizations

# ------------------ Whitelist Management ------------------

whitelist = set()

def load_whitelist():
    global whitelist
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, "r") as f:
            try:
                whitelist = set(json.load(f))
            except:
                whitelist = set()
    else:
        whitelist = set()

def save_whitelist():
    with open(WHITELIST_FILE, "w") as f:
        json.dump(list(whitelist), f, indent=2)

def add_to_whitelist(process_name: str):
    whitelist.add(process_name)
    save_whitelist()

def remove_from_whitelist(process_name: str):
    whitelist.discard(process_name)
    save_whitelist()

def is_whitelisted(process_name: str) -> bool:
    return process_name in whitelist

# ------------------ Optimization Tracking ------------------

def record_optimization(proc_name, cpu_before, mem_before):
    """Record how much optimization (freed CPU + RAM) was achieved."""
    try:
        cpu_after = psutil.cpu_percent(interval=0.1)
        mem_after = psutil.virtual_memory().percent

        cpu_gain = max(0, cpu_before - cpu_after)
        mem_gain = max(0, mem_before - mem_after)
        gain = round((cpu_gain * 0.6 + mem_gain * 0.4), 2)

        OPTIMIZATION_LOG.append({
            "process": proc_name,
            "cpu_gain": cpu_gain,
            "mem_gain": mem_gain,
            "optimization": gain,
            "timestamp": time.strftime("%H:%M:%S")
        })
        return gain

    except Exception:
        return 0.0

def get_recent_optimizations():
    """Return the last few optimization records."""
    return list(OPTIMIZATION_LOG)

import psutil, time, subprocess, json, os
from utils import log_event, ts

# ----------------------------------------
# 🔒 System-level Ignore List
# ----------------------------------------
IGNORE = [
    "System", "Registry", "svchost.exe", "smss.exe",
    "wininit.exe", "lsass.exe", "csrss.exe", "services.exe"
]

# ----------------------------------------
# 🧠 Restart Mapping
# ----------------------------------------
RESTART_MAP = {
    "notepad.exe": ["notepad.exe"],
    "calc.exe": ["calc.exe"],
}

# ----------------------------------------
# 📜 Whitelist Config
# ----------------------------------------
WHITELIST_FILE = "whitelist.json"

def load_whitelist():
    """Safely load user whitelist (case-insensitive)."""
    try:
        if os.path.exists(WHITELIST_FILE):
            with open(WHITELIST_FILE, "r") as f:
                data = json.load(f)
                # normalize case
                return [str(p).strip().lower() for p in data]
    except Exception as e:
        log_event(f"⚠️ Failed to read whitelist.json: {e}")
    return []

def is_whitelisted(name: str, whitelist: list):
    """Check if process name matches any whitelisted entry (case-insensitive)."""
    return name.lower().strip() in whitelist

# ----------------------------------------
# ⚙️ Optimization Data Tracking
# ----------------------------------------
OPTIMIZATION_FILE = "optimization_data.json"

def record_optimization(process_name, cpu_before, mem_before, cpu_after, mem_after):
    cpu_gain = max(0, cpu_before - cpu_after)
    mem_gain = max(0, mem_before - mem_after)
    optimization_score = (cpu_gain + mem_gain) / 2

    try:
        data = []
        if os.path.exists(OPTIMIZATION_FILE):
            with open(OPTIMIZATION_FILE, "r") as f:
                data = json.load(f)
        data.append({
            "timestamp": ts(),
            "process": process_name,
            "cpu_gain": round(cpu_gain, 2),
            "mem_gain": round(mem_gain, 2),
            "optimization_score": round(optimization_score, 2)
        })
        with open(OPTIMIZATION_FILE, "w") as f:
            json.dump(data[-50:], f, indent=2)
        log_event(f"📈 Optimization for {process_name}: {optimization_score:.2f}%")
    except Exception as e:
        log_event(f"⚠️ Failed to record optimization for {process_name}: {e}")

# ----------------------------------------
# 🧩 Responsiveness & Healing Logic
# ----------------------------------------
def is_process_unresponsive(proc):
    try:
        if proc.cpu_percent(interval=0.1) == 0 and proc.memory_percent() < 1:
            return True
        return False
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False

def heal_process(proc, whitelist):
    try:
        name = proc.name()
        pid = proc.pid
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return

    # 🔒 Skip whitelisted apps immediately
    if is_whitelisted(name, whitelist):
        log_event(f"🚫 Skipped whitelisted process: {name} (PID {pid})")
        return

    # snapshot before healing
    cpu_before = proc.cpu_percent(interval=0.1)
    mem_before = proc.memory_percent()

    try:
        log_event(f"🩺 Attempting to heal process: {name} (PID {pid})")
        proc.terminate()
        proc.wait(timeout=5)
        log_event(f"✅ Terminated unresponsive process: {name} (PID {pid})")

        # optional restart
        if name.lower() in RESTART_MAP:
            try:
                subprocess.Popen(RESTART_MAP[name.lower()])
                log_event(f"🔁 Restarted process: {name}")
            except Exception as e:
                log_event(f"❌ Restart failed for {name} -> {e}")

        # record optimization gain
        time.sleep(1)
        cpu_after = psutil.cpu_percent(interval=0.1)
        mem_after = psutil.virtual_memory().percent
        record_optimization(name, cpu_before, mem_before, cpu_after, mem_after)

    except Exception as e:
        log_event(f"❌ Healing failed for {name} (PID {pid}) -> {e}")

# ----------------------------------------
# 🧠 Main Loop
# ----------------------------------------
def main():
    log_event("🧠 Healer service started", f"Timestamp: {ts()}")

    while True:
        whitelist = load_whitelist()  # 🔁 Always refresh dynamically

        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pname = proc.info.get("name", "")
                if not pname or pname in IGNORE:
                    continue

                # Skip whitelisted user-defined processes
                if is_whitelisted(pname, whitelist):
                    continue

                if is_process_unresponsive(proc):
                    heal_process(proc, whitelist)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        time.sleep(10)

if __name__ == "__main__":
    main()

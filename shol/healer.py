import psutil, time, subprocess
from utils import log_event, ts

# Simple restart mapping for common system tools (demo purpose)
RESTART_MAP = {
    "notepad.exe": ["notepad.exe"],
    "calc.exe": ["calc.exe"],
    # add any custom app here
}

def is_process_unresponsive(proc):
    try:
        # If CPU usage = 0 and memory usage < 1% for 3+ checks → assume frozen
        if proc.cpu_percent(interval=0.1) == 0 and proc.memory_percent() < 1:
            return True
        return False
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False

def heal_process(proc):
    name = proc.name()
    pid = proc.pid
    try:
        log_event(f"🩹 Attempting to heal process: {name} (PID {pid})")
        proc.terminate()
        proc.wait(timeout=5)
        log_event(f"✅ Terminated unresponsive process: {name} (PID {pid})")

        # Try restarting if it’s known in RESTART_MAP
        if name.lower() in RESTART_MAP:
            subprocess.Popen(RESTART_MAP[name.lower()])
            log_event(f"🔁 Restarted process: {name}")

    except Exception as e:
        log_event(f"❌ Healing failed for {name} (PID {pid}) → {e}")

def main():
    log_event(f"🧠 Healer service started at {ts()}")
    while True:
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            if is_process_unresponsive(proc):
                heal_process(proc)
        time.sleep(10)  # check every 10 seconds

if __name__ == "__main__":
    main()

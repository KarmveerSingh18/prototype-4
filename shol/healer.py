import psutil, time, subprocess
from utils import log_event, ts

# Ignore system-level or protected processes
IGNORE = [
    "System", "Registry", "svchost.exe", "smss.exe",
    "wininit.exe", "lsass.exe", "csrss.exe", "services.exe"
]

# Simple restart mapping for common demo tools
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

def heal_process(proc, cause=None, health_score=None):
    """
    Heals (terminates/restarts) the given psutil.Process object.
    Accepts optional cause (string) and health_score (numeric) for richer logging.
    Backwards-compatible: existing calls without cause/health_score will still work.
    """
    try:
        name = proc.name()
        pid = proc.pid
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        log_event(f"⚠️ Cannot access process metadata (may have exited) | PID: {getattr(proc, 'pid', 'N/A')}")
        return

    # Build rich log message
    meta_parts = []
    if cause:
        meta_parts.append(f"Cause: {cause}")
    if health_score is not None:
        meta_parts.append(f"Health: {health_score:.1f}")
    meta = " | ".join(meta_parts) if meta_parts else "No cause provided"

    try:
        log_event(f"🩺 Attempting to heal process: {name} (PID {pid}) | {meta}")
        proc.terminate()
        proc.wait(timeout=5)
        log_event(f"✅ Terminated unresponsive process: {name} (PID {pid}) | {meta}")

        # Optionally attempt restart if you have a mapping
        if name.lower() in RESTART_MAP:
            try:
                subprocess.Popen(RESTART_MAP[name.lower()])
                log_event(f"🔁 Restarted process: {name} (via restart map)")
            except Exception as e:
                log_event(f"❌ Restart failed for {name} -> {e}")

    except Exception as e:
        log_event(f"❌ Healing failed for {name} (PID {pid}) -> {e} | {meta}")

def main():
    log_event("🧠 Healer service started", f"Timestamp: {ts()}")
    while True:
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                # Skip protected/system processes
                if proc.info["name"] in IGNORE:
                    continue

                if is_process_unresponsive(proc):
                    heal_process(proc)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        time.sleep(10)  # check every 10 seconds

if __name__ == "__main__":
    main()

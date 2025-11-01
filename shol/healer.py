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
        log_event(f" Failed to read whitelist.json: {e}")
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
        log_event(f" Optimization for {process_name}: {optimization_score:.2f}%")
    except Exception as e:
        log_event(f" Failed to record optimization for {process_name}: {e}")

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
    import os  # ensure os is available locally
    try:
        name = proc.name()
        pid = proc.pid
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return

    # 🔒 Skip whitelisted apps
    if is_whitelisted(name, whitelist):
        log_event(f" Skipped whitelisted process: {name} (PID {pid})")
        return

    try:
        # ✅ Capture system usage before healing
        cpu_before = psutil.cpu_percent(interval=0.8)
        mem_before = psutil.virtual_memory().percent

        log_event(f" Attempting to heal process: {name} (PID {pid})")

        # -----------------------
        # 🩹 SOFT RECOVERY (cross-platform safe)
        # -----------------------
        recovery_type = "Soft Recovery"
        try:
            # Get current niceness/priority
            try:
                current_nice = proc.nice()
            except Exception:
                current_nice = None

            # Platform-specific lowering of priority:
            if os.name == "nt":
                # Windows: use priority class constants
                # Build a safe downward-mapping (higher index -> LOWER priority)
                win_map = {
                    psutil.REALTIME_PRIORITY_CLASS: psutil.HIGH_PRIORITY_CLASS,
                    psutil.HIGH_PRIORITY_CLASS: psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                    psutil.ABOVE_NORMAL_PRIORITY_CLASS: psutil.NORMAL_PRIORITY_CLASS,
                    psutil.NORMAL_PRIORITY_CLASS: psutil.BELOW_NORMAL_PRIORITY_CLASS,
                    psutil.BELOW_NORMAL_PRIORITY_CLASS: psutil.IDLE_PRIORITY_CLASS,
                    psutil.IDLE_PRIORITY_CLASS: psutil.IDLE_PRIORITY_CLASS
                }
                # fallback: if current_nice not one of these, choose BELOW_NORMAL
                try:
                    new_nice = win_map.get(current_nice, psutil.BELOW_NORMAL_PRIORITY_CLASS)
                    proc.nice(new_nice)
                    log_event(f" [Soft Recovery] Lowered priority of {name} (PID {pid}) from {current_nice} → {new_nice}")
                except Exception as e:
                    # try a conservative default
                    try:
                        proc.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                        log_event(f" [Soft Recovery] Applied conservative BELOW_NORMAL for {name} (PID {pid})")
                    except Exception as e2:
                        raise e2
            else:
                # Unix-like: nice values -20 (high priority) .. 19 (low priority).
                # Increasing numeric nice lowers priority.
                try:
                    if current_nice is None:
                        current_nice = proc.nice()
                    # increase niceness by 5 (but not beyond 19)
                    new_nice = min(int(current_nice) + 5, 19)
                    proc.nice(new_nice)
                    log_event(f" [Soft Recovery] Lowered priority of {name} (PID {pid}) from {current_nice} → {new_nice}")
                except Exception:
                    # fallback: try a safe niceness
                    try:
                        proc.nice(10)
                        log_event(f" [Soft Recovery] Set niceness=10 for {name} (PID {pid}) as fallback")
                    except Exception as e:
                        raise e

            # Wait briefly and recheck system CPU to judge effectiveness
            time.sleep(2.5)
            cpu_after_soft = psutil.cpu_percent(interval=0.8)

            # If CPU usage improved significantly (here threshold: 30% drop), consider success
            if cpu_after_soft < cpu_before * 0.7:
                log_event(f" [Soft Recovery Success] {name}: CPU improved {cpu_before:.2f}% → {cpu_after_soft:.2f}%")
                mem_after_soft = psutil.virtual_memory().percent
                record_optimization(name, cpu_before, mem_before, cpu_after_soft, mem_after_soft)
                log_event(f" {recovery_type} successful for {name} (PID {pid})")
                return
            else:
                log_event(f" [Soft Recovery Ineffective] {name} still high usage ({cpu_after_soft:.2f}%)")

        except Exception as e:
            # Log the specific soft-recovery error (this prevents WinError 87 from crashing the function)
            log_event(f" [Soft Recovery Failed] {name}: {e}")

        # -----------------------
        # 💀 HARD RECOVERY — terminate if soft failed
        # -----------------------
        recovery_type = "Hard Recovery"
        try:
            proc.terminate()
            proc.wait(timeout=5)
            log_event(f" [Hard Recovery] Terminated unresponsive process: {name} (PID {pid})")
        except Exception as tere:
            # if terminate fails, try kill as last resort (but log it)
            try:
                proc.kill()
                log_event(f" [Hard Recovery] Killed process as fallback: {name} (PID {pid})")
            except Exception as e:
                log_event(f" Termination/Kill failed for {name} (PID {pid}) -> {e}")
                # can't proceed to optimization recording if kill failed; return
                return

        # 🔁 Optional restart
        if name.lower() in RESTART_MAP:
            try:
                subprocess.Popen(RESTART_MAP[name.lower()])
                log_event(f" Restarted process: {name}")
            except Exception as e:
                log_event(f" Restart failed for {name} -> {e}")

        # ✅ Wait for system to stabilize
        time.sleep(1.5)
        cpu_after = psutil.cpu_percent(interval=0.8)
        mem_after = psutil.virtual_memory().percent

        # Calculate optimization
        cpu_gain = max(0, cpu_before - cpu_after)
        mem_gain = max(0, mem_before - mem_after)
        optimization_score = round((cpu_gain + mem_gain) / 2, 2)

        record_optimization(name, cpu_before, mem_before, cpu_after, mem_after)

        # Log summary for dashboard
        if optimization_score > 0.05:
            log_event(f" [{recovery_type}] Optimization for {name}: {optimization_score:.2f}% (CPU↓ {cpu_gain:.2f}%, MEM↓ {mem_gain:.2f}%)")
        else:
            log_event(f"ℹ [{recovery_type}] Minimal optimization for {name}: <0.1%")

    except Exception as e:
        log_event(f" Healing failed for {name} (PID {pid}) -> {e}")



# ----------------------------------------
# 🧠 Main Loop
# ----------------------------------------
def main():
    log_event(" Healer service started", f"Timestamp: {ts()}")

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

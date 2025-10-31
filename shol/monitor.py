import psutil, time, os, datetime, subprocess
from collections import deque, defaultdict
from utils import ts
# keep short history per pid
HISTORY_LEN = 60   # samples (~60 * poll interval)

class ProcessHistory:
    def __init__(self):
        # pid -> deque of dict snapshots
        self.hist = defaultdict(lambda: deque(maxlen=HISTORY_LEN))

    def sample(self):
        snapshot_time = ts()
        for p in psutil.process_iter(['pid','name','cmdline','cpu_percent','memory_percent','status']):
            try:
                info = p.info
                info['sample_ts'] = snapshot_time
                # normalize cmdline to string
                info['cmdline_str'] = " ".join(info.get('cmdline') or [])
                self.hist[info['pid']].append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # process died or permission
                continue

    def get_latest(self, pid):
        h = self.hist.get(pid)
        return h[-1] if h else None

    def get_all_latest(self):
        results = []
        for pid, dq in self.hist.items():
            if dq:
                results.append(dq[-1])
        return results

    def cleanup_dead(self):
        # remove pids not present in current system
        current_pids = set(p.pid for p in psutil.process_iter())
        for pid in list(self.hist.keys()):
            if pid not in current_pids:
                del self.hist[pid]


# --- 1️⃣ Create log folder and file path ---
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "events.log")
os.makedirs(LOG_DIR, exist_ok=True)   # Creates logs/ if not already present


# --- 2️⃣ Function to log crash/restart events ---
def log_event(process_name, cause="Unknown"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{now}] Restarted {process_name} | Cause: {cause}\n")


# --- 3️⃣ Function to restart crashed processes ---
def restart_process(exe_path, process_name, cause="Unknown"):
    try:
        subprocess.Popen(exe_path)   # Launch the process again
        log_event(process_name, cause)
        print(f"✅ Restarted {process_name}")
    except Exception as e:
        print(f"❌ Failed to restart {process_name}: {e}")


# --- 4️⃣ Core monitoring loop (sample demo) ---
def monitor_system():
    watched_processes = {
        "notepad.exe": r"C:\Windows\System32\notepad.exe",  # Example
    }

    while True:
        for pname, path in watched_processes.items():
            running = any(p.info['name'].lower() == pname.lower() for p in psutil.process_iter(['name']))
            if not running:
                restart_process(path, pname, cause="Process not found / crashed")
        time.sleep(5)  # check every 5 seconds


def check_process(proc):
    try:
        cpu = proc.cpu_percent() / psutil.cpu_count()
        mem = proc.memory_percent()

        cause = None
        if cpu > 85:
            cause = f"High CPU Usage ({cpu:.1f}%)"
        elif mem > 80:
            cause = f"High Memory Usage ({mem:.1f}%)"
        elif not proc.is_running():
            cause = "Process Not Responding"

        if cause:
            from healer import heal_process
            heal_process(proc, cause)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass


def get_health_score(cpu, mem):
    score = max(0, 100 - (cpu*0.6 + mem*0.4))
    if score > 80:
        status = "Healthy"
    elif score > 60:
        status = "Warning"
    else:
        status = "Critical"
    return score, status




if __name__ == "__main__":
    monitor_system()

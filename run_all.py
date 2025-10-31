import subprocess
import time
import os
import sys

# Force UTF-8 encoding for Windows terminal and subprocesses
os.environ["PYTHONUTF8"] = "1"
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Paths to scripts
MONITOR_PATH = os.path.join("shol", "monitor.py")
HEALER_PATH = os.path.join("shol", "healer.py")
DASHBOARD_PATH = os.path.join("web", "dashboard.py")

# Start monitor
print("Starting Monitor...")
monitor_proc = subprocess.Popen(["python", MONITOR_PATH])

# Wait a moment to let it start cleanly
time.sleep(2)

# Start healer
print("Starting Healer...")
healer_proc = subprocess.Popen(["python", HEALER_PATH])

# Wait again before opening dashboard
time.sleep(2)

# Start dashboard
print("Opening Dashboard...")
dashboard_proc = subprocess.Popen(["python", DASHBOARD_PATH])

print("\n[OK] All systems running. Press Ctrl+C to stop everything.\n")

try:
    # Keep script running while processes are alive
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n Shutting down all processes...")
    monitor_proc.terminate()
    healer_proc.terminate()
    dashboard_proc.terminate()

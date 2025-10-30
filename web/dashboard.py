import tkinter as tk
from tkinter import ttk, scrolledtext
import psutil, threading, time, os

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "events.log")

class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🧠 Self-Healing OS Dashboard")
        self.geometry("900x600")
        self.configure(bg="#101820")

        # Title
        tk.Label(
            self, text="System Health Monitor", 
            font=("Segoe UI", 18, "bold"), fg="#00FFAA", bg="#101820"
        ).pack(pady=10)

        # System stats
        self.stats_label = tk.Label(
            self, text="", font=("Consolas", 12), fg="#FFFFFF", bg="#101820"
        )
        self.stats_label.pack(pady=10)

        # Log viewer
        frame = tk.Frame(self, bg="#101820")
        frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.log_area = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, font=("Consolas", 10),
            bg="#0E1621", fg="#00FFAA", insertbackground="white"
        )
        self.log_area.pack(fill="both", expand=True)
        self.log_area.insert("end", "[Dashboard Ready]\n")
        self.log_area.configure(state="disabled")

        # Start background threads
        threading.Thread(target=self.update_stats, daemon=True).start()
        threading.Thread(target=self.tail_log, daemon=True).start()

    def update_stats(self):
        while True:
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent

            stats_text = f"CPU: {cpu}%   |   Memory: {mem}%   |   Disk: {disk}%"
            self.stats_label.config(text=stats_text)
            time.sleep(1)

    def tail_log(self):
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if line:
                    self.log_area.configure(state="normal")
                    self.log_area.insert("end", line)
                    self.log_area.configure(state="disabled")
                    self.log_area.yview("end")
                time.sleep(0.5)

if __name__ == "__main__":
    app = Dashboard()
    app.mainloop()

import customtkinter as ctk
from tkinter import *
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading, time, os, re
from collections import Counter

# === Theme ===
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Healing Event Dashboard")
root.geometry("1400x800")

ACCENT = "#3BAFDA"
BG_COLOR = "#121212"
BOX_BG = "#1E1E1E"
root.configure(fg_color=BG_COLOR)

# === Title ===
title_label = ctk.CTkLabel(root, text="Healing Event Monitor", font=("Segoe UI", 30, "bold"), text_color=ACCENT)
title_label.pack(pady=(20, 10))

# === Layout Frames ===
main_frame = ctk.CTkFrame(root, fg_color=BOX_BG, corner_radius=20)
main_frame.pack(fill="both", expand=True, padx=30, pady=20)

main_frame.columnconfigure(0, weight=2)
main_frame.columnconfigure(1, weight=1)
main_frame.rowconfigure(0, weight=1)

# === Live Events ===
live_events_frame = ctk.CTkFrame(main_frame, fg_color="#181818", corner_radius=20)
live_events_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

live_title = ctk.CTkLabel(live_events_frame, text="Live Events", font=("Segoe UI", 22, "bold"), text_color=ACCENT)
live_title.pack(pady=(10, 10))

live_events_box = Text(live_events_frame, bg="#101010", fg="#FFFFFF", insertbackground="white",
                       font=("Consolas", 13), height=25, wrap="word", bd=0, relief="flat")
live_events_box.pack(fill="both", expand=True, padx=20, pady=10)
live_events_box.insert("end", "Loading real-time healing events...\n")

# === Analytics ===
analytics_frame = ctk.CTkFrame(main_frame, fg_color="#181818", corner_radius=20)
analytics_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

analytics_title = ctk.CTkLabel(analytics_frame, text="Analytics Overview", font=("Segoe UI", 22, "bold"), text_color=ACCENT)
analytics_title.pack(pady=(10, 10))

analytics_box = ctk.CTkTextbox(analytics_frame, fg_color="#101010", text_color="#FFFFFF", font=("Consolas", 13))
analytics_box.pack(fill="x", padx=20, pady=10)

# --- Graph placeholder ---
fig = Figure(figsize=(4.5, 3), facecolor="#101010")
ax = fig.add_subplot(111)
ax.set_facecolor("#101010")
ax.tick_params(colors="white")
ax.spines['bottom'].set_color(ACCENT)
ax.spines['left'].set_color(ACCENT)
ax.set_title("Healing Events Over Time", color=ACCENT, fontsize=12)
canvas = FigureCanvasTkAgg(fig, master=analytics_frame)
canvas.draw()
canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=10)

# === Footer ===
footer_label = ctk.CTkLabel(root, text="© 2025 Healing Systems Monitor", font=("Segoe UI", 12), text_color="#777")
footer_label.pack(pady=10)

# === Paths ===
LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "logs", "events.log")
start_time = time.time()

# === Functions ===
def analyze_events(log_text):
    lines = log_text.splitlines()
    healings, timestamps = [], []
    for line in lines:
        if "Healing" in line:
            match_time = re.match(r"\[(.*?)\]", line)
            if match_time:
                timestamps.append(match_time.group(1))
            healings.append(line)
    return len(healings), timestamps

def update_live_events():
    while True:
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                data = f.read()
            live_events_box.delete("1.0", "end")
            live_events_box.insert("end", data)
            live_events_box.see("end")
        except Exception as e:
            live_events_box.delete("1.0", "end")
            live_events_box.insert("end", f"Error reading log: {e}")
        time.sleep(2)

def update_analytics():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            data = f.read()
        total, timestamps = analyze_events(data)

        analytics_box.delete("1.0", "end")
        uptime = int(time.time() - start_time)
        analytics_box.insert("end", f"Total Healing Events: {total}\n")
        analytics_box.insert("end", f"System Uptime: {uptime // 3600:02}:{(uptime // 60) % 60:02}:{uptime % 60:02}\n")

        # Update chart
        ax.clear()
        ax.set_facecolor("#101010")
        ax.spines['bottom'].set_color(ACCENT)
        ax.spines['left'].set_color(ACCENT)
        ax.tick_params(colors="white")
        ax.plot(range(len(timestamps)), range(1, len(timestamps) + 1), color=ACCENT, linewidth=2)
        ax.set_title("Healing Events Over Time", color=ACCENT)
        canvas.draw()
    except Exception as e:
        analytics_box.insert("end", f"Error: {e}\n")

    root.after(5000, update_analytics)  # every 5 sec

# === Start Threads ===
threading.Thread(target=update_live_events, daemon=True).start()
root.after(2000, update_analytics)

root.mainloop()

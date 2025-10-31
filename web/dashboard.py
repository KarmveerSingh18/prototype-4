# dashboard.py
import os
import threading
import time
import re
import json
import tkinter as tk
from collections import Counter, deque
from datetime import datetime

import customtkinter as ctk
from tkinter import Text
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import numpy as np
import psutil
import GPUtil

# GPUtil optional
try:
    import GPUtil
    _GPUMON_AVAILABLE = True
except Exception:
    _GPUMON_AVAILABLE = False

# ---------------- Config ----------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

APP_BG = "#08090b"
CARD_BG = "#0f1722"
LOG_BG = "#0b0f12"
ACCENT = "#00C8B4"
ACCENT2 = "#38BDF8"
TEXT_COLOR = "#E6EEF3"

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "logs", "events.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# new data files for whitelist and optimization log
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
WHITELIST_FILE = os.path.join(DATA_DIR, "whitelist.json")
OPT_LOG_FILE = os.path.join(DATA_DIR, "optimization_log.json")

# ensure files exist
if not os.path.exists(WHITELIST_FILE):
    with open(WHITELIST_FILE, "w") as _f:
        json.dump([], _f)
if not os.path.exists(OPT_LOG_FILE):
    with open(OPT_LOG_FILE, "w") as _f:
        json.dump([], _f)

# Sampling history length (seconds)
HISTORY_LEN = 120

# ---------------- App ----------------
root = ctk.CTk()
root.title("HealOS — Dashboard")
root.geometry("1400x820")
root.minsize(1000, 700)
root.configure(fg_color=APP_BG)

# ---------- Layout ----------
title = ctk.CTkLabel(root, text="HealOS — Self-Healing Monitor", font=("Segoe UI", 26, "bold"), text_color=ACCENT)
title.pack(pady=(12, 8))

main = ctk.CTkFrame(root, fg_color=APP_BG, corner_radius=0)
main.pack(fill="both", expand=True, padx=18, pady=(6, 18))

main.grid_columnconfigure(0, weight=3)
main.grid_columnconfigure(1, weight=1)
main.grid_rowconfigure(0, weight=1)

# ----- Left (Live Monitor) -----
left_card = ctk.CTkFrame(main, fg_color=CARD_BG, corner_radius=12)
left_card.grid(row=0, column=0, sticky="nsew", padx=(10,8), pady=10)
left_card.grid_rowconfigure(3, weight=1)
left_card.grid_columnconfigure(0, weight=1)

live_lbl = ctk.CTkLabel(left_card, text="Live Monitor", font=("Segoe UI", 18, "bold"), text_color=ACCENT)
live_lbl.grid(row=0, column=0, sticky="w", padx=14, pady=(12,4))

# Live status row: CPU / MEM / GPU percentages
status_frame = ctk.CTkFrame(left_card, fg_color="#091015", corner_radius=8)
status_frame.grid(row=1, column=0, sticky="ew", padx=14, pady=(4,10))
status_frame.grid_columnconfigure(0, weight=1)
status_frame.grid_columnconfigure(1, weight=1)
status_frame.grid_columnconfigure(2, weight=1)

cpu_label = ctk.CTkLabel(status_frame, text="CPU: --%", font=("Consolas", 12))
cpu_label.grid(row=0, column=0, padx=12, pady=8, sticky="w")
cpu_bar = ctk.CTkProgressBar(status_frame, width=320)
cpu_bar.grid(row=1, column=0, padx=12, pady=(0,12), sticky="w")

mem_label = ctk.CTkLabel(status_frame, text="Memory: --%", font=("Consolas", 12))
mem_label.grid(row=0, column=1, padx=12, pady=8, sticky="w")
mem_bar = ctk.CTkProgressBar(status_frame, width=320)
mem_bar.grid(row=1, column=1, padx=12, pady=(0,12), sticky="w")

gpu_label = ctk.CTkLabel(status_frame, text="GPU: N/A", font=("Consolas", 12))
gpu_label.grid(row=0, column=2, padx=12, pady=8, sticky="w")
gpu_bar = ctk.CTkProgressBar(status_frame, width=320)
gpu_bar.grid(row=1, column=2, padx=12, pady=(0,12), sticky="w")

# Log area
log_title = ctk.CTkLabel(left_card, text="Live Event Logs", font=("Segoe UI", 16, "bold"), text_color=ACCENT2)
log_title.grid(row=2, column=0, sticky="w", padx=14)

log_container = ctk.CTkFrame(left_card, fg_color=LOG_BG, corner_radius=10)
log_container.grid(row=3, column=0, sticky="nsew", padx=14, pady=12)
log_container.grid_rowconfigure(0, weight=1)
log_container.grid_columnconfigure(0, weight=1)

log_box = Text(log_container, bg=LOG_BG, fg=TEXT_COLOR, insertbackground=ACCENT, font=("Consolas", 12), wrap="word", bd=0, relief="flat")
log_box.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
log_box.insert("end", "Waiting for events...\n")

# ----- Right (Analytics summary + open-analytics-button) -----
right_card = ctk.CTkFrame(main, fg_color=CARD_BG, corner_radius=12)
right_card.grid(row=0, column=1, sticky="nsew", padx=(8,10), pady=10)
right_card.grid_rowconfigure(2, weight=1)
right_card.grid_columnconfigure(0, weight=1)

analytics_lbl = ctk.CTkLabel(right_card, text="Analytics Summary", font=("Segoe UI", 18, "bold"), text_color=ACCENT)
analytics_lbl.grid(row=0, column=0, sticky="w", padx=14, pady=(12,6))

sub_lbl = ctk.CTkLabel(right_card, text="Top offenders · total heals · uptime", text_color="#9fb6b0")
sub_lbl.grid(row=1, column=0, sticky="w", padx=14)

summary_box = ctk.CTkTextbox(right_card, fg_color=LOG_BG, text_color=TEXT_COLOR, font=("Consolas", 11))
summary_box.grid(row=2, column=0, sticky="nsew", padx=14, pady=(8,12))
summary_box.insert("end", "Loading analytics...\n")

# we keep original Open Analytics button
open_analytics_btn = ctk.CTkButton(right_card, text="Open Analytics Window", command=lambda: open_analytics_window(), fg_color=ACCENT, hover_color=ACCENT2)
open_analytics_btn.grid(row=3, column=0, padx=14, pady=(6,6))

# NEW: Open Whitelist Manager button (placed under Analytics button)
def open_whitelist_manager():
    # popup to manage whitelist.json
    win = ctk.CTkToplevel(root)
    win.title("Whitelist Manager")
    win.geometry("420x360")
    win.configure(fg_color=APP_BG)

    # load whitelist
    try:
        with open(WHITELIST_FILE, "r") as f:
            wl = json.load(f)
    except Exception:
        wl = []

    def save_and_refresh():
        with open(WHITELIST_FILE, "w") as f:
            json.dump(wl, f, indent=2)
        refresh_list()

    def refresh_list():
        listbox.delete(0, tk.END)
        for item in wl:
            listbox.insert(tk.END, item)

    def add_item():
        name = entry.get().strip().lower()
        if name and name not in wl:
            wl.append(name)
            save_and_refresh()
            entry.delete(0, tk.END)

    def remove_item():
        sel = listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        try:
            wl.pop(idx)
        except Exception:
            pass
        save_and_refresh()

    header = ctk.CTkLabel(win, text="Process Whitelist", font=("Segoe UI", 16, "bold"), text_color=ACCENT)
    header.pack(pady=(12,6))

    listbox = tk.Listbox(win, bg="#0b0f12", fg=TEXT_COLOR, highlightthickness=0, selectbackground="#08312f", bd=0)
    listbox.pack(fill="both", expand=False, padx=18, pady=(6,6), ipady=4)
    refresh_list()

    entry = ctk.CTkEntry(win, placeholder_text="e.g. chrome.exe (case-insensitive)")
    entry.pack(fill="x", padx=18, pady=(6,6))

    btn_frame = ctk.CTkFrame(win, fg_color=APP_BG)
    btn_frame.pack(pady=(6,12))
    add_btn = ctk.CTkButton(btn_frame, text="Add", command=add_item, fg_color=ACCENT)
    add_btn.grid(row=0, column=0, padx=6)
    rem_btn = ctk.CTkButton(btn_frame, text="Remove Selected", command=remove_item, fg_color="#ff6b6b")
    rem_btn.grid(row=0, column=1, padx=6)

ctk.CTkButton(right_card, text="Whitelist Manager", command=open_whitelist_manager, fg_color="#10b981", hover_color="#34d399").grid(row=4, column=0, padx=14, pady=(6,12))

footer = ctk.CTkLabel(root, text="© 2025 Healing Systems Monitor", font=("Segoe UI", 10), text_color="#7b8b87")
footer.pack(side="bottom", pady=(6,12))

# ---------------- Data buffers ----------------
cpu_hist = deque(maxlen=HISTORY_LEN)
mem_hist = deque(maxlen=HISTORY_LEN)
gpu_hist = deque(maxlen=HISTORY_LEN)
time_hist = deque(maxlen=HISTORY_LEN)

start_time = time.time()

# ---------------- Helpers: log parsing ----------------
def parse_log_for_metrics(text):
    lines = text.splitlines()
    healings = []
    offenders = []
    times = []
    for ln in lines:
        # consider attempt/terminate/healed lines
        if any(k in ln for k in ("Healing", "Terminated", "Attempting to heal", "✅", "Attempting")):
            healings.append(ln)
            m = re.search(r'Process:\s*([\w\.\-]+)', ln)
            if not m:
                m = re.search(r'process:\s*([\w\.\-]+)', ln, re.IGNORECASE)
            if m:
                offenders.append(m.group(1))
            t = re.match(r'\[(.*?)\]', ln)
            if t:
                times.append(t.group(1))
    return healings, offenders, times

# ---------------- Background: poll system stats ----------------
def sample_stats_loop():
    while True:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        gpu = None
        if _GPUMON_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = sum(g.memoryUtil for g in gpus) / len(gpus) * 100.0
                else:
                    gpu = None
            except Exception:
                gpu = None

        tnow = time.time()
        cpu_hist.append(cpu)
        mem_hist.append(mem)
        gpu_hist.append(gpu if gpu is not None else 0.0)
        time_hist.append(tnow)

        # update main UI labels (schedule on main thread)
        def apply():
            cpu_label.configure(text=f"CPU: {int(cpu)}%")
            cpu_bar.set(cpu / 100.0)
            mem_label.configure(text=f"Memory: {int(mem)}%")
            mem_bar.set(mem / 100.0)
            if gpu is not None:
                gpu_label.configure(text=f"GPU: {int(gpu)}%")
                gpu_bar.set(gpu / 100.0)
            else:
                gpu_label.configure(text="GPU: N/A")
                gpu_bar.set(0.0)
        root.after(0, apply)

        # loop continues (psutil already waited 1s via cpu_percent interval)

# ---------------- Background: update log box ----------------
def update_log_box_loop():
    while True:
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    data = f.read()
            else:
                data = "No events logged yet.\n"
            def apply():
                log_box.delete("1.0", "end")
                log_box.insert("end", data)
                log_box.see("end")
            root.after(0, apply)
        except Exception as e:
            def err_apply():
                log_box.delete("1.0", "end")
                log_box.insert("end", f"Error reading log: {e}\n")
            root.after(0, err_apply)
        time.sleep(2)

# ---------------- Update analytics summary on right card ----------------
def update_analytics_summary():
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read()
        else:
            raw = ""
        healings, offenders, times = parse_log_for_metrics(raw)
        total = len(healings)
        c = Counter(offenders)
        top5 = c.most_common(5)
        uptime = int(time.time() - start_time)
        uh = f"{uptime//3600:02}:{(uptime//60)%60:02}:{uptime%60:02}"
        summary_box.delete("1.0", "end")
        summary_box.insert("end", f"Total healing events: {total}\n\n")
        if top5:
            summary_box.insert("end", "Top offenders:\n")
            for p, cnt in top5:
                summary_box.insert("end", f" • {p}: {cnt}\n")
        else:
            summary_box.insert("end", "Top offenders: none\n")
        summary_box.insert("end", f"\nUptime: {uh}\n")
    except Exception as e:
        summary_box.insert("end", f"\nAnalytics error: {e}\n")
    root.after(3000, update_analytics_summary)

# ---------------- Floating analytics window (opens on demand) ----------------
analytics_window = None

def open_analytics_window():
    global analytics_window
    # if window exists, bring to front
    if analytics_window and analytics_window.winfo_exists():
        analytics_window.lift()
        return

    # create floating window
    analytics_window = ctk.CTkToplevel(root)
    analytics_window.title("System Performance — Live Charts")
    analytics_window.geometry("1200x840")
    analytics_window.configure(fg_color=APP_BG)

    # layout: three charts side-by-side
    frame = ctk.CTkFrame(analytics_window, fg_color=CARD_BG, corner_radius=12)
    frame.pack(fill="both", expand=True, padx=12, pady=12)
    frame.grid_columnconfigure((0,1,2), weight=1)
    frame.grid_rowconfigure(0, weight=1)

    # create matplotlib figs for CPU, GPU, MEM
    figs = []
    canvases = []
    axes = []

    for i, label in enumerate(("CPU Usage", "GPU Usage", "Memory Usage")):
        fig = Figure(figsize=(4,3), facecolor="#071018", dpi=100)
        ax = fig.add_subplot(111)
        ax.set_facecolor("#071018")
        ax.tick_params(colors="#9fb6b0")
        for spine in ax.spines.values():
            spine.set_color("#12333a")
        ax.set_title(label, color=ACCENT, fontsize=11)
        canvas = FigureCanvasTkAgg(fig, master=frame)
        widget = canvas.get_tk_widget()
        widget.grid(row=0, column=i, sticky="nsew", padx=8, pady=8)
        figs.append(fig); canvases.append(canvas); axes.append(ax)

    # ---------------- Process optimization (bar chart) ----------------
    # create separate area under the three charts
    proc_frame = ctk.CTkFrame(analytics_window, fg_color=CARD_BG, corner_radius=12)
    proc_frame.pack(fill="x", expand=False, padx=12, pady=(0,12))
    proc_label = ctk.CTkLabel(proc_frame, text="Optimization Impact by Process (last 10)", text_color=ACCENT, font=("Segoe UI", 12, "bold"))
    proc_label.pack(anchor="w", padx=12, pady=(8,4))

    proc_fig = Figure(figsize=(11,2.8), facecolor="#071018", dpi=100)
    proc_ax = proc_fig.add_subplot(111)
    proc_ax.set_facecolor("#071018")
    proc_ax.tick_params(colors="#9fb6b0")
    for spine in proc_ax.spines.values():
        spine.set_color("#12333a")
    proc_ax.set_title("", color=ACCENT, fontsize=10)

    proc_canvas = FigureCanvasTkAgg(proc_fig, master=proc_frame)
    proc_widget = proc_canvas.get_tk_widget()
    proc_widget.pack(fill="both", expand=True, padx=8, pady=(0,12))

    def refresh_charts():
        # prepare arrays
        xlen = len(time_hist)
        xs = np.arange(xlen)

        # CPU
        axes[0].clear()
        axes[0].set_facecolor("#071018")
        axes[0].tick_params(colors="#9fb6b0")
        axes[0].set_title("CPU Usage", color=ACCENT, fontsize=11)
        if xlen > 0:
            y = np.array(list(cpu_hist))
            # simple robust plot
            axes[0].plot(xs, y, color=ACCENT, lw=2)
            axes[0].scatter(xs, y, s=20, c=ACCENT, edgecolors="#08312f", linewidths=0.4, zorder=3)
            axes[0].set_ylim(0, 100)
            axes[0].set_xlim(max(0, xlen-60), max(60, xlen))  # show last up to 60 samples
        else:
            axes[0].text(0.5,0.5,"No data",ha="center",va="center", color="#7f8a86")

        # GPU
        axes[1].clear()
        axes[1].set_facecolor("#071018")
        axes[1].tick_params(colors="#9fb6b0")
        axes[1].set_title("GPU Usage", color=ACCENT, fontsize=11)
        if _GPUMON_AVAILABLE and xlen > 0:
            y = np.array(list(gpu_hist))
            axes[1].plot(xs, y, color=ACCENT2, lw=2)
            axes[1].scatter(xs, y, s=20, c=ACCENT2, edgecolors="#062a3a", linewidths=0.4, zorder=3)
            axes[1].set_ylim(0, 100)
            axes[1].set_xlim(max(0, xlen-60), max(60, xlen))
        else:
            axes[1].text(0.5,0.5,"GPU N/A",ha="center",va="center", color="#7f8a86")

        # Memory
        axes[2].clear()
        axes[2].set_facecolor("#071018")
        axes[2].tick_params(colors="#9fb6b0")
        axes[2].set_title("Memory Usage", color=ACCENT, fontsize=11)
        if xlen > 0:
            y = np.array(list(mem_hist))
            axes[2].plot(xs, y, color="#00e6cf", lw=2)
            axes[2].scatter(xs, y, s=20, c="#00e6cf", edgecolors="#05332f", linewidths=0.4, zorder=3)
            axes[2].set_ylim(0, 100)
            axes[2].set_xlim(max(0, xlen-60), max(60, xlen))
        else:
            axes[2].text(0.5,0.5,"No data",ha="center",va="center", color="#7f8a86")

        for canvas in canvases:
            canvas.draw()

        # --- update process optimization bar chart ---
        try:
            with open(OPT_LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                opt_data = json.load(f)
        except Exception:
            opt_data = []

        # take last 10 entries grouped by process (we'll display last 10 events)
        last_n = opt_data[-10:] if opt_data else []
        if last_n:
            procs = [d.get("process", d.get("proc", "unknown")) for d in last_n]
            gains = [float(d.get("optimization", 0.0)) for d in last_n]
            proc_ax.clear()
            proc_ax.set_facecolor("#071018")
            proc_ax.tick_params(colors="#9fb6b0")
            bars = proc_ax.bar(range(len(procs)), gains, color="#00e6cf")
            proc_ax.set_ylim(min(0, min(gains) - 1), max(10, max(gains) + 5))
            proc_ax.set_xticks(range(len(procs)))
            proc_ax.set_xticklabels(procs, rotation=30, fontsize=9)
            proc_ax.set_ylabel("Optimization (%)", color="#9fb6b0")
            proc_ax.set_title("Optimization Impact by Process (last 10)", color=ACCENT, fontsize=11)
            # label bars
            for rect, val in zip(bars, gains):
                height = rect.get_height()
                proc_ax.text(rect.get_x() + rect.get_width()/2.0, height + 0.5, f"+{val}%", ha='center', va='bottom', color="#e6fff9", fontsize=8)
        else:
            proc_ax.clear()
            proc_ax.set_facecolor("#071018")
            proc_ax.text(0.5, 0.5, "No optimization data yet", ha="center", va="center", color="#7f8a86")

        proc_canvas.draw()

        # schedule next update
        if analytics_window and analytics_window.winfo_exists():
            analytics_window.after(1000, refresh_charts)

    # start refresh
    analytics_window.after(500, refresh_charts)

# ---------------- Start background threads & loop updates ----------------
threading.Thread(target=sample_stats_loop, daemon=True).start()
threading.Thread(target=update_log_box_loop, daemon=True).start()
root.after(1000, update_analytics_summary)

# ---------------- Run ----------------
root.mainloop()

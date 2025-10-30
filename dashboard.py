import tkinter as tk, psutil
from tkinter import ttk
from threading import Thread
from monitor import SystemMonitor  # your core script

root = tk.Tk()
root.title("Self-Healing OS Layer")

tree = ttk.Treeview(root, columns=('pid','name','cpu'), show='headings')
for col in ('pid','name','cpu'):
    tree.heading(col, text=col.upper())
tree.pack(fill='both', expand=True)

def refresh():
    tree.delete(*tree.get_children())
    for p in psutil.process_iter(['pid','name','cpu_percent']):
        tree.insert('', 'end', values=(p.info['pid'], p.info['name'], p.info['cpu_percent']))
    root.after(2000, refresh)

Thread(target=SystemMonitor().run, daemon=True).start()
refresh()
root.mainloop()

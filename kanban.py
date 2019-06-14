#!/usr/bin/env python3
# kanban-local - work in progress

import tkinter as tk

COLS = ["To Do", "In Progress", "Done"]
BG     = "#f4f4f4"
COL_BG = "#e2e8ee"

root = tk.Tk()
root.title("kanban-local")
root.geometry("900x580")
root.configure(bg=BG)

for col in COLS:
    f = tk.Frame(root, bg=COL_BG, width=260)
    f.pack(side="left", fill="y", padx=8, pady=10)
    f.pack_propagate(False)
    tk.Label(f, text=col, bg=COL_BG,
             font=("Segoe UI", 10, "bold")).pack(padx=8, pady=10, anchor="w")

root.mainloop()

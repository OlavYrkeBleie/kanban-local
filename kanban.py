#!/usr/bin/env python3
# kanban-local

import tkinter as tk
from tkinter import messagebox, simpledialog
import re

COLS   = ["To Do", "In Progress", "Done"]
APP_BG = "#f4f4f4"
COL_BG = "#e2e8ee"
CARD_W = 230

class Card:
    def __init__(self, title, body=""):
        self.title = title
        self.body  = body
        self.tags  = re.findall(r'@(\w+)', body)

cards = {c: [] for c in COLS}
col_frames = {}

def refresh():
    for col, frame in col_frames.items():
        for w in frame.winfo_children():
            w.destroy()
        for card in cards[col]:
            build_card(frame, card, col)

def build_card(parent, card, col):
    f = tk.Frame(parent, bg="white", relief="raised", bd=1)
    f.pack(fill="x", padx=6, pady=4)
    tk.Label(f, text=card.title, bg="white",
             font=("Segoe UI", 9, "bold"), wraplength=CARD_W-20).pack(anchor="w", padx=6, pady=(5,2))
    if card.body:
        tk.Label(f, text=card.body, bg="white", font=("Segoe UI", 8),
                 wraplength=CARD_W-20, fg="#555").pack(anchor="w", padx=8, pady=(0,3))
    bf = tk.Frame(f, bg="white")
    bf.pack(fill="x", padx=4, pady=(0,4))
    ci = COLS.index(col)
    if ci > 0:
        tk.Button(bf, text="←", bd=0, bg="#e8e8e8",
                  command=lambda c=card,fc=col,tc=COLS[ci-1]: move(c,fc,tc)).pack(side="left", padx=1)
    if ci < len(COLS)-1:
        tk.Button(bf, text="→", bd=0, bg="#e8e8e8",
                  command=lambda c=card,fc=col,tc=COLS[ci+1]: move(c,fc,tc)).pack(side="left", padx=1)
    tk.Button(bf, text="✕", bd=0, bg="#ffd0d0",
              command=lambda c=card,co=col: delete(c,co)).pack(side="right", padx=1)

def move(card, from_col, to_col):
    cards[from_col].remove(card)
    cards[to_col].append(card)
    refresh()

def delete(card, col):
    if messagebox.askyesno("Delete", f'Delete "{card.title}"?'):
        cards[col].remove(card)
        refresh()

def add_card(col):
    title = simpledialog.askstring("New card", "Title:", parent=root)
    if title and title.strip():
        body = simpledialog.askstring("New card", "Notes (@tag to mention):", parent=root) or ""
        cards[col].append(Card(title.strip(), body))
        refresh()

root = tk.Tk()
root.title("kanban-local")
root.geometry("900x580")
root.configure(bg=APP_BG)

for col in COLS:
    outer = tk.Frame(root, bg=COL_BG, width=270)
    outer.pack(side="left", fill="y", padx=8, pady=10)
    outer.pack_propagate(False)
    hdr = tk.Frame(outer, bg=COL_BG)
    hdr.pack(fill="x", padx=6, pady=(8,4))
    tk.Label(hdr, text=col, bg=COL_BG, font=("Segoe UI", 9, "bold")).pack(side="left")
    tk.Button(hdr, text="+", bd=0, bg=COL_BG,
              font=("Segoe UI", 13, "bold"), fg="#27ae60",
              command=lambda c=col: add_card(c)).pack(side="right")
    inner = tk.Frame(outer, bg=COL_BG)
    inner.pack(fill="both", expand=True)
    col_frames[col] = inner

root.mainloop()

#!/usr/bin/env python3
# kanban-local

import tkinter as tk
from tkinter import messagebox, simpledialog
import json, os, re

COLS    = ["To Do","In Progress","Done"]
APP_BG  = "#f4f4f4"
COL_BG  = "#e2e8ee"
CARD_W  = 230
TAG_FG  = "#1565c0"
TAG_BG  = "#e3f2fd"
DATA_DIR  = os.path.join(os.path.expanduser("~"),".kanban-local")
SAVE_PATH = os.path.join(DATA_DIR,"data.json")

class Card:
    def __init__(self,title,body=""):
        self.title=title; self.body=body
        self.tags=re.findall(r'@(\w+)',body)
    def to_dict(self): return {"title":self.title,"body":self.body}
    @classmethod
    def from_dict(cls,d): return cls(d["title"],d.get("body",""))

board={c:[] for c in COLS}
col_frames={}

def save():
    os.makedirs(DATA_DIR,exist_ok=True)
    with open(SAVE_PATH,"w") as f:
        json.dump({c:[card.to_dict() for card in board[c]] for c in COLS},f,indent=2)

def load():
    if os.path.exists(SAVE_PATH):
        try:
            with open(SAVE_PATH) as f: data=json.load(f)
            for c in COLS: board[c]=[Card.from_dict(d) for d in data.get(c,[])]
        except Exception: pass

def refresh():
    for col,frame in col_frames.items():
        for w in frame.winfo_children(): w.destroy()
        for card in board[col]: build_card(frame,card,col)

def build_card(parent,card,col):
    f=tk.Frame(parent,bg="white",relief="raised",bd=1)
    f.pack(fill="x",padx=6,pady=4)
    tk.Label(f,text=card.title,bg="white",font=("Segoe UI",9,"bold"),
             wraplength=CARD_W-20).pack(anchor="w",padx=6,pady=(5,2))
    if card.body:
        tk.Label(f,text=card.body,bg="white",font=("Segoe UI",8),
                 wraplength=CARD_W-20,fg="#555").pack(anchor="w",padx=8,pady=(0,2))
    if card.tags:
        tf=tk.Frame(f,bg="white"); tf.pack(anchor="w",padx=8,pady=(0,3))
        for tag in card.tags:
            tk.Label(tf,text="@"+tag,bg=TAG_BG,fg=TAG_FG,
                     font=("Segoe UI",7),padx=3,pady=1).pack(side="left",padx=2)
    bf=tk.Frame(f,bg="white"); bf.pack(fill="x",padx=4,pady=(0,4))
    ci=COLS.index(col)
    if ci>0: tk.Button(bf,text="←",bd=0,bg="#e8e8e8",
        command=lambda c=card,fc=col,tc=COLS[ci-1]:move(c,fc,tc)).pack(side="left",padx=1)
    if ci<len(COLS)-1: tk.Button(bf,text="→",bd=0,bg="#e8e8e8",
        command=lambda c=card,fc=col,tc=COLS[ci+1]:move(c,fc,tc)).pack(side="left",padx=1)
    tk.Button(bf,text="✕",bd=0,bg="#ffd0d0",
              command=lambda c=card,co=col:delete(c,co)).pack(side="right",padx=1)

def move(card,from_col,to_col):
    board[from_col].remove(card); board[to_col].append(card); save(); refresh()

def delete(card,col):
    if messagebox.askyesno("Delete",f'Delete "{card.title}"?'):
        board[col].remove(card); save(); refresh()

def add_card(col):
    t=simpledialog.askstring("New card","Title:",parent=root)
    if t and t.strip():
        b=simpledialog.askstring("New card","Notes (@tag to mention):",parent=root) or ""
        board[col].append(Card(t.strip(),b)); save(); refresh()

def export_json():
    data=json.dumps({c:[card.to_dict() for card in board[c]] for c in COLS},indent=2)
    root.clipboard_clear(); root.clipboard_append(data)
    messagebox.showinfo("Exported","Board JSON copied to clipboard.\nImport on another machine to merge.",parent=root)

def import_json():
    try:
        data=json.loads(root.clipboard_get())
        added=0
        for c in COLS:
            existing={card.title for card in board[c]}
            for d in data.get(c,[]):
                if d["title"] not in existing:
                    board[c].append(Card.from_dict(d)); added+=1
        save(); refresh()
        messagebox.showinfo("Imported",f"Added {added} card(s) from clipboard.",parent=root)
    except Exception as ex:
        messagebox.showerror("Error",f"Could not parse:\n{ex}",parent=root)

root=tk.Tk(); root.title("kanban-local"); root.geometry("960x600"); root.configure(bg=APP_BG)
load()

try:
    from PIL import ImageGrab
    PIL_OK=True
except ImportError:
    PIL_OK=False


top=tk.Frame(root,bg="#2c3e50",height=38); top.pack(fill="x"); top.pack_propagate(False)
tk.Label(top,text="kanban-local",bg="#2c3e50",fg="white",
         font=("Segoe UI",11,"bold")).pack(side="left",padx=12,pady=8)
tk.Button(top,text="Export JSON",command=export_json,bg="#27ae60",fg="white",
          bd=0,padx=8,pady=3).pack(side="right",padx=4,pady=5)
tk.Button(top,text="Import JSON",command=import_json,bg="#27ae60",fg="white",
          bd=0,padx=8,pady=3).pack(side="right",padx=2,pady=5)

def screenshot():
    if not PIL_OK:
        from tkinter import messagebox
        messagebox.showerror("Error","pip install pillow"); return
    root.update()
    img=ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),
        root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height()))
    import os; path=os.path.join(os.path.expanduser("~"),"Desktop","kanban.png")
    img.save(path)
    from tkinter import messagebox
    messagebox.showinfo("Saved",f"Saved to {path}")
tk.Button(top,text="Screenshot",command=screenshot,bg="#2980b9",fg="white",
          bd=0,padx=8,pady=3).pack(side="right",padx=4,pady=5)

main=tk.Frame(root,bg=APP_BG); main.pack(fill="both",expand=True)

for col in COLS:
    outer=tk.Frame(main,bg=COL_BG,width=280); outer.pack(side="left",fill="y",padx=8,pady=10)
    outer.pack_propagate(False)
    hdr=tk.Frame(outer,bg=COL_BG); hdr.pack(fill="x",padx=6,pady=(8,4))
    tk.Label(hdr,text=col,bg=COL_BG,font=("Segoe UI",9,"bold")).pack(side="left")
    tk.Button(hdr,text="+",bd=0,bg=COL_BG,font=("Segoe UI",13,"bold"),fg="#27ae60",
              command=lambda c=col:add_card(c)).pack(side="right")
    inner=tk.Frame(outer,bg=COL_BG); inner.pack(fill="both",expand=True)
    col_frames[col]=inner

refresh()
root.mainloop()

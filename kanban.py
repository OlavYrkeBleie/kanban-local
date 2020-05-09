#!/usr/bin/env python3
"""
kanban-local
local kanban board with calendar, json sharing, screenshot export.
auto-saves to ~/.kanban-local/data.json
build to exe: pyinstaller --onefile --windowed --name kanban kanban.py
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import json, os, re, datetime, uuid

try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ── config ────────────────────────────────────────────────────────────────────
DATA_DIR    = os.path.join(os.path.expanduser("~"), ".kanban-local")
DATA_FILE   = os.path.join(DATA_DIR, "data.json")
AUTOSAVE_MS = 30_000

COLUMNS = ["To Do", "In Progress", "Done"]

STATUS = {
    "grey":   {"bg": "#eeeeee", "dot": "#9e9e9e", "text": "Planning"},
    "green":  {"bg": "#c8e6c9", "dot": "#43a047", "text": "On schedule"},
    "yellow": {"bg": "#fff9c4", "dot": "#f9a825", "text": "On hold"},
    "red":    {"bg": "#ffcdd2", "dot": "#e53935", "text": "Stopped"},
}
CYCLE = ["grey", "green", "yellow", "red"]

APP_BG     = "#f4f4f4"
SIDEBAR_BG = "#1e2a38"
SIDEBAR_SEL= "#2e4057"
TOPBAR_BG  = "#2c3e50"
COL_BG     = "#e2e8ee"
TAG_FG     = "#1565c0"
TAG_BG     = "#e3f2fd"
CARD_W     = 215

# ── model ─────────────────────────────────────────────────────────────────────
def new_id(): return str(uuid.uuid4())[:8]

class Card:
    def __init__(self, title, body="", status="grey", tags=None, cid=None):
        self.id=cid or new_id(); self.title=title; self.body=body
        self.status=status; self.tags=tags or re.findall(r'@(\w+)',body)
    def to_dict(self):
        return {"id":self.id,"title":self.title,"body":self.body,
                "status":self.status,"tags":self.tags}
    @classmethod
    def from_dict(cls,d):
        return cls(d["title"],d.get("body",""),d.get("status","grey"),
                   d.get("tags",[]),d.get("id"))

class Board:
    def __init__(self, name="Board", bid=None):
        self.id=bid or new_id(); self.name=name
        self.columns={c:[] for c in COLUMNS}
    def to_dict(self):
        return {"id":self.id,"name":self.name,
                "columns":{c:[card.to_dict() for card in cards]
                           for c,cards in self.columns.items()}}
    @classmethod
    def from_dict(cls,d):
        b=cls(d["name"],d.get("id"))
        for col in COLUMNS:
            b.columns[col]=[Card.from_dict(c) for c in d.get("columns",{}).get(col,[])]
        return b

class CalDay:
    def __init__(self,text="",events=None): self.text=text; self.events=events or []
    def to_dict(self): return {"text":self.text,"events":self.events}
    @classmethod
    def from_dict(cls,d): return cls(d.get("text",""),d.get("events",[]))

class AppData:
    def __init__(self):
        self.boards=[Board("My Board")]; self.calendar={}
    def to_dict(self):
        return {"boards":[b.to_dict() for b in self.boards],
                "calendar":{k:v.to_dict() for k,v in self.calendar.items()}}
    @classmethod
    def from_dict(cls,d):
        ad=cls()
        ad.boards=[Board.from_dict(b) for b in d.get("boards",[])] or [Board("My Board")]
        ad.calendar={k:CalDay.from_dict(v) for k,v in d.get("calendar",{}).items()}
        return ad
    def save(self):
        os.makedirs(DATA_DIR,exist_ok=True)
        with open(DATA_FILE,"w") as f: json.dump(self.to_dict(),f,indent=2)
    @classmethod
    def load(cls):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE) as f: return cls.from_dict(json.load(f))
            except Exception: pass
        return cls()

# ── dialogs ───────────────────────────────────────────────────────────────────
class CardDialog(tk.Toplevel):
    def __init__(self, parent, card=None):
        super().__init__(parent)
        self.title("Edit Card" if card else "New Card")
        self.resizable(False,False); self.result=None; self.configure(bg=APP_BG); self.grab_set()
        pad={"padx":10,"pady":4}
        tk.Label(self,text="Title",bg=APP_BG,font=("Segoe UI",9,"bold")).grid(row=0,column=0,sticky="w",**pad)
        self.tv=tk.StringVar(value=card.title if card else "")
        tk.Entry(self,textvariable=self.tv,width=34,font=("Segoe UI",9)).grid(row=0,column=1,**pad)
        tk.Label(self,text="Notes\n(@name to tag)",bg=APP_BG,font=("Segoe UI",9)).grid(row=1,column=0,sticky="nw",**pad)
        self.body=tk.Text(self,width=34,height=5,font=("Segoe UI",9),wrap="word")
        self.body.grid(row=1,column=1,**pad)
        if card and card.body: self.body.insert("1.0",card.body)
        bf=tk.Frame(self,bg=APP_BG); bf.grid(row=2,column=0,columnspan=2,pady=8)
        tk.Button(bf,text="Save",command=self._save,width=10,bg="#27ae60",fg="white",bd=0).pack(side="left",padx=6)
        tk.Button(bf,text="Cancel",command=self.destroy,width=10,bg="#7f8c8d",fg="white",bd=0).pack(side="left",padx=6)
        self.wait_window()
    def _save(self):
        t=self.tv.get().strip()
        if not t: return
        b=self.body.get("1.0","end-1c").strip()
        self.result={"title":t,"body":b,"tags":re.findall(r'@(\w+)',b)}; self.destroy()

class DayDialog(tk.Toplevel):
    def __init__(self, parent, date_str, day):
        super().__init__(parent)
        self.title(date_str); self.resizable(False,False); self.result=None
        self.configure(bg=APP_BG); self.grab_set()
        self.events=[ev["title"] for ev in day.events]
        tk.Label(self,text=date_str,bg=APP_BG,font=("Segoe UI",11,"bold")).pack(padx=12,pady=(10,4))
        ef=tk.LabelFrame(self,text="Events",bg=APP_BG,font=("Segoe UI",9))
        ef.pack(fill="x",padx=12,pady=4)
        self.lb=tk.Listbox(ef,height=4,font=("Segoe UI",9),width=34); self.lb.pack(side="left",padx=4,pady=4)
        for e in day.events: self.lb.insert("end",e["title"])
        ebf=tk.Frame(ef,bg=APP_BG); ebf.pack(side="left",fill="y",padx=4)
        tk.Button(ebf,text="+ Add",command=self._add,width=8,bg="#3498db",fg="white",bd=0).pack(pady=2)
        tk.Button(ebf,text="Delete",command=self._del,width=8,bg="#e74c3c",fg="white",bd=0).pack(pady=2)
        tk.Label(self,text="Notes",bg=APP_BG,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=12)
        self.notes=tk.Text(self,width=36,height=4,font=("Segoe UI",9)); self.notes.pack(padx=12,pady=4)
        self.notes.insert("1.0",day.text)
        bf=tk.Frame(self,bg=APP_BG); bf.pack(pady=8)
        tk.Button(bf,text="Save",command=self._save,width=10,bg="#27ae60",fg="white",bd=0).pack(side="left",padx=6)
        tk.Button(bf,text="Cancel",command=self.destroy,width=10,bg="#7f8c8d",fg="white",bd=0).pack(side="left",padx=6)
        self.wait_window()
    def _add(self):
        t=simpledialog.askstring("Event","Title:",parent=self)
        if t and t.strip(): self.events.append(t.strip()); self.lb.insert("end",t.strip())
    def _del(self):
        sel=self.lb.curselection()
        if sel: self.events.pop(sel[0]); self.lb.delete(sel[0])
    def _save(self):
        self.result={"text":self.notes.get("1.0","end-1c").strip(),
                     "events":[{"title":e} for e in self.events]}; self.destroy()

# ── card widget ───────────────────────────────────────────────────────────────
class CardWidget(tk.Frame):
    def __init__(self, parent, card, col, app):
        bg=STATUS[card.status]["bg"]
        super().__init__(parent,bg=bg,relief="raised",bd=1,cursor="hand2")
        self.card=card; self.col=col; self.app=app; self._build()

    def _build(self):
        for w in self.winfo_children(): w.destroy()
        bg=STATUS[self.card.status]["bg"]; self.configure(bg=bg)
        top=tk.Frame(self,bg=bg); top.pack(fill="x",padx=6,pady=(6,2))
        dot=tk.Label(top,text="●",bg=bg,fg=STATUS[self.card.status]["dot"],
                     font=("Segoe UI",11),cursor="hand2")
        dot.pack(side="left"); dot.bind("<Button-1>",lambda e:self._cycle())
        tk.Label(top,text=self.card.title,bg=bg,font=("Segoe UI",9,"bold"),
                 wraplength=CARD_W-50,justify="left").pack(side="left",padx=4)
        if self.card.body:
            tk.Label(self,text=self.card.body,bg=bg,font=("Segoe UI",8),
                     wraplength=CARD_W-20,justify="left",fg="#444").pack(anchor="w",padx=10,pady=(0,2))
        if self.card.tags:
            tf=tk.Frame(self,bg=bg); tf.pack(anchor="w",padx=8,pady=(0,2))
            for tag in self.card.tags:
                tk.Label(tf,text="@"+tag,bg=TAG_BG,fg=TAG_FG,
                         font=("Segoe UI",7),padx=3,pady=1).pack(side="left",padx=2)
        tk.Label(self,text=STATUS[self.card.status]["text"],bg=bg,
                 font=("Segoe UI",7),fg="#666").pack(anchor="w",padx=10,pady=(0,2))
        bf=tk.Frame(self,bg=bg); bf.pack(fill="x",padx=5,pady=(0,5))
        ci=COLUMNS.index(self.col)
        if ci>0: tk.Button(bf,text="←",bd=0,bg="#d8d8d8",font=("Segoe UI",8),
                            command=self._left,padx=3).pack(side="left",padx=1)
        if ci<len(COLUMNS)-1: tk.Button(bf,text="→",bd=0,bg="#d8d8d8",font=("Segoe UI",8),
                            command=self._right,padx=3).pack(side="left",padx=1)
        tk.Button(bf,text="edit",bd=0,bg="#d8d8d8",font=("Segoe UI",8),
                  command=self._edit,padx=4).pack(side="left",padx=1)
        tk.Button(bf,text="✕",bd=0,bg="#f5b7b1",font=("Segoe UI",8),
                  command=self._delete,padx=3).pack(side="right",padx=1)

    def _cycle(self):
        self.card.status=CYCLE[(CYCLE.index(self.card.status)+1)%len(CYCLE)]
        self._build(); self.app.autosave()
    def _left(self): self.app.move_card(self.card,self.col,COLUMNS[COLUMNS.index(self.col)-1])
    def _right(self): self.app.move_card(self.card,self.col,COLUMNS[COLUMNS.index(self.col)+1])
    def _edit(self):
        dlg=CardDialog(self.app.root,self.card)
        if dlg.result:
            self.card.title=dlg.result["title"]; self.card.body=dlg.result["body"]
            self.card.tags=dlg.result["tags"]; self.app.rebuild_board(); self.app.autosave()
    def _delete(self):
        if messagebox.askyesno("Delete",f'Delete "{self.card.title}"?',parent=self.app.root):
            self.app.current_board.columns[self.col].remove(self.card)
            self.app.rebuild_board(); self.app.autosave()

# ── calendar panel ────────────────────────────────────────────────────────────
class CalPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent,bg=APP_BG); self.app=app
        self.today=datetime.date.today(); self.year=self.today.year; self.month=self.today.month
        self._build()

    def _build(self):
        for w in self.winfo_children(): w.destroy()
        nav=tk.Frame(self,bg=APP_BG); nav.pack(fill="x",padx=12,pady=8)
        tk.Button(nav,text="◀",bd=0,bg=APP_BG,command=self._prev).pack(side="left")
        tk.Label(nav,text=datetime.date(self.year,self.month,1).strftime("%B %Y"),
                 bg=APP_BG,font=("Segoe UI",11,"bold")).pack(side="left",expand=True)
        tk.Button(nav,text="▶",bd=0,bg=APP_BG,command=self._next).pack(side="right")
        grid=tk.Frame(self,bg=APP_BG); grid.pack(padx=12)
        for i,d in enumerate(["Mo","Tu","We","Th","Fr","Sa","Su"]):
            tk.Label(grid,text=d,bg=APP_BG,font=("Segoe UI",8,"bold"),
                     width=7,fg="#555").grid(row=0,column=i,padx=1,pady=1)
        import calendar
        for r,week in enumerate(calendar.monthcalendar(self.year,self.month)):
            for c,day in enumerate(week):
                if day==0:
                    tk.Label(grid,bg=APP_BG,width=7,height=4).grid(row=r+1,column=c,padx=1,pady=1); continue
                ds=f"{self.year}-{self.month:02d}-{day:02d}"
                obj=self.app.data.calendar.get(ds,CalDay())
                istoday=(datetime.date(self.year,self.month,day)==self.today)
                cbg="#d5f5e3" if istoday else ("#dbeafe" if (obj.events or obj.text) else "white")
                cell=tk.Frame(grid,bg=cbg,width=58,height=56,relief="solid",bd=1,cursor="hand2")
                cell.grid(row=r+1,column=c,padx=1,pady=1); cell.pack_propagate(False)
                tk.Label(cell,text=str(day),bg=cbg,
                         font=("Segoe UI",9,"bold" if istoday else "normal")).pack(anchor="nw",padx=2)
                for ev in obj.events[:2]:
                    tk.Label(cell,text="·"+ev["title"][:9],bg=cbg,
                             font=("Segoe UI",7),fg="#154360").pack(anchor="w",padx=2)
                for child in [cell]+cell.winfo_children():
                    child.bind("<Button-1>",lambda e,s=ds:self._day(s))
        up=tk.LabelFrame(self,text="Upcoming",bg=APP_BG,font=("Segoe UI",9))
        up.pack(fill="x",padx=12,pady=8)
        items=[(k,ev["title"]) for k,v in sorted(self.app.data.calendar.items())
               for ev in v.events if k>=str(self.today)][:5]
        for ds,t in items:
            tk.Label(up,text=f"  {ds}  {t}",bg=APP_BG,font=("Segoe UI",8),anchor="w").pack(fill="x")
        if not items:
            tk.Label(up,text="  no upcoming events",bg=APP_BG,font=("Segoe UI",8),fg="#888").pack(anchor="w")

    def _prev(self):
        self.month=12 if self.month==1 else self.month-1
        if self.month==12: self.year-=1
        self._build()
    def _next(self):
        self.month=1 if self.month==12 else self.month+1
        if self.month==1: self.year+=1
        self._build()
    def _day(self, ds):
        obj=self.app.data.calendar.get(ds,CalDay())
        dlg=DayDialog(self.app.root,ds,obj)
        if dlg.result:
            self.app.data.calendar[ds]=CalDay.from_dict(dlg.result)
            self.app.autosave(); self._build()

# ── main app ──────────────────────────────────────────────────────────────────
class KanbanApp:
    def __init__(self, root):
        self.root=root; self.root.title("kanban-local")
        self.root.geometry("1100x660"); self.root.minsize(800,500)
        self.root.configure(bg=APP_BG)
        self.root.protocol("WM_DELETE_WINDOW",self._close)
        self.data=AppData.load()
        self.current_board=self.data.boards[0]
        self.view="board"; self.col_frames={}
        self._build_ui(); self._autosave_loop()

    def _close(self):
        ans=messagebox.askyesnocancel("kanban-local",
            "Yes = quit and save\nNo = minimize to taskbar\nCancel = go back",
            parent=self.root)
        if ans is True:   self.data.save(); self.root.destroy()
        elif ans is False: self.root.iconify()

    def autosave(self): self.data.save()
    def _autosave_loop(self): self.data.save(); self.root.after(AUTOSAVE_MS,self._autosave_loop)

    def _build_ui(self):
        self.sidebar=tk.Frame(self.root,bg=SIDEBAR_BG,width=180)
        self.sidebar.pack(side="left",fill="y"); self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar,text="kanban-local",bg=SIDEBAR_BG,fg="white",
                 font=("Segoe UI",10,"bold")).pack(pady=(14,6),padx=10)
        self.board_list=tk.Frame(self.sidebar,bg=SIDEBAR_BG); self.board_list.pack(fill="x")
        tk.Frame(self.sidebar,bg="#ffffff22",height=1).pack(fill="x",padx=10,pady=4)
        cal=tk.Label(self.sidebar,text="📅  Calendar",bg=SIDEBAR_BG,fg="#aab",
                     cursor="hand2",font=("Segoe UI",9),anchor="w",padx=14)
        cal.pack(fill="x",pady=2); cal.bind("<Button-1>",lambda e:self._view("calendar"))
        tk.Frame(self.sidebar,bg="#ffffff22",height=1).pack(fill="x",padx=10,pady=4)
        nb=tk.Label(self.sidebar,text="＋  New Board",bg=SIDEBAR_BG,fg="#aab",
                    cursor="hand2",font=("Segoe UI",9),anchor="w",padx=14)
        nb.pack(fill="x",pady=2); nb.bind("<Button-1>",lambda e:self._new_board())
        self.main=tk.Frame(self.root,bg=APP_BG); self.main.pack(side="left",fill="both",expand=True)
        self._build_topbar()
        self.content=tk.Frame(self.main,bg=APP_BG); self.content.pack(fill="both",expand=True)
        self._refresh_sidebar(); self._view("board")

    def _build_topbar(self):
        top=tk.Frame(self.main,bg=TOPBAR_BG,height=40)
        top.pack(fill="x"); top.pack_propagate(False)
        self.title_var=tk.StringVar(value=self.current_board.name)
        te=tk.Entry(top,textvariable=self.title_var,font=("Segoe UI",11,"bold"),
                    bd=0,bg=TOPBAR_BG,fg="white",insertbackground="white",width=26)
        te.pack(side="left",padx=14,pady=8)
        te.bind("<Return>",self._rename); te.bind("<FocusOut>",self._rename)
        for txt,cmd,col in [("📷 Screenshot",self._screenshot,"#2980b9"),
                             ("⬇ Import",self._import_json,"#27ae60"),
                             ("⬆ Export",self._export_json,"#27ae60")]:
            tk.Button(top,text=txt,command=cmd,bg=col,fg="white",bd=0,
                      font=("Segoe UI",8),padx=8,pady=3,cursor="hand2").pack(side="right",padx=3,pady=5)

    def _refresh_sidebar(self):
        for w in self.board_list.winfo_children(): w.destroy()
        for b in self.data.boards:
            sel=(b is self.current_board and self.view=="board")
            bg=SIDEBAR_SEL if sel else SIDEBAR_BG
            lbl=tk.Label(self.board_list,text="📋  "+b.name,bg=bg,fg="white",
                         font=("Segoe UI",9),anchor="w",padx=14,cursor="hand2")
            lbl.pack(fill="x",pady=1); lbl.bind("<Button-1>",lambda e,b=b:self._select(b))

    def _view(self, v):
        self.view=v
        for w in self.content.winfo_children(): w.destroy()
        if v=="board": self.rebuild_board()
        else: CalPanel(self.content,self).pack(fill="both",expand=True)
        self._refresh_sidebar()

    def _select(self, board): self.current_board=board; self._view("board"); self.title_var.set(board.name)
    def _new_board(self):
        n=simpledialog.askstring("New Board","Name:",parent=self.root)
        if n and n.strip():
            b=Board(n.strip()); self.data.boards.append(b); self._select(b); self.autosave()
    def _rename(self, e=None):
        n=self.title_var.get().strip()
        if n: self.current_board.name=n; self._refresh_sidebar(); self.autosave()

    def rebuild_board(self):
        for w in self.content.winfo_children(): w.destroy()
        self.col_frames={}
        for col in COLUMNS:
            outer=tk.Frame(self.content,bg=COL_BG,width=CARD_W+32)
            outer.pack(side="left",fill="y",padx=8,pady=10); outer.pack_propagate(False)
            hdr=tk.Frame(outer,bg=COL_BG); hdr.pack(fill="x",padx=6,pady=(8,4))
            cnt=len(self.current_board.columns[col])
            tk.Label(hdr,text=f"{col}  ({cnt})",bg=COL_BG,
                     font=("Segoe UI",9,"bold")).pack(side="left")
            tk.Button(hdr,text="+",bd=0,bg=COL_BG,font=("Segoe UI",13,"bold"),fg="#27ae60",
                      cursor="hand2",command=lambda c=col:self.add_card(c)).pack(side="right")
            cv=tk.Canvas(outer,bg=COL_BG,highlightthickness=0)
            sb=tk.Scrollbar(outer,orient="vertical",command=cv.yview)
            inner=tk.Frame(cv,bg=COL_BG)
            inner.bind("<Configure>",lambda e,cv=cv:cv.configure(scrollregion=cv.bbox("all")))
            cv.create_window((0,0),window=inner,anchor="nw")
            cv.configure(yscrollcommand=sb.set)
            cv.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
            self.col_frames[col]=inner
            for card in self.current_board.columns[col]:
                CardWidget(inner,card,col,self).pack(fill="x",padx=6,pady=4)

    def add_card(self, col):
        dlg=CardDialog(self.root)
        if dlg.result:
            self.current_board.columns[col].append(
                Card(dlg.result["title"],dlg.result["body"],tags=dlg.result["tags"]))
            self.rebuild_board(); self.autosave()

    def move_card(self, card, from_col, to_col):
        self.current_board.columns[from_col].remove(card)
        self.current_board.columns[to_col].append(card)
        self.rebuild_board(); self.autosave()

    def _screenshot(self):
        if not PIL_AVAILABLE:
            messagebox.showerror("Missing","pip install pillow",parent=self.root); return
        self.root.update()
        x=self.root.winfo_rootx(); y=self.root.winfo_rooty()
        img=ImageGrab.grab(bbox=(x,y,x+self.root.winfo_width(),y+self.root.winfo_height()))
        path=os.path.join(os.path.expanduser("~"),"Desktop","kanban_screenshot.png")
        img.save(path)
        messagebox.showinfo("Saved",f"Screenshot saved to Desktop.\nOpen and paste into Discord.",parent=self.root)

    def _export_json(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(json.dumps(self.current_board.to_dict(),indent=2))
        messagebox.showinfo("Exported","Board JSON copied to clipboard.\nOther person: Import JSON to merge.",parent=self.root)

    def _import_json(self):
        try:
            other=Board.from_dict(json.loads(self.root.clipboard_get()))
            added=0
            for col in COLUMNS:
                existing={c.title for c in self.current_board.columns[col]}
                for card in other.columns.get(col,[]):
                    if card.title not in existing:
                        self.current_board.columns[col].append(card); added+=1
            self.rebuild_board(); self.autosave()
            messagebox.showinfo("Imported",f"Added {added} card(s).",parent=self.root)
        except Exception as ex:
            messagebox.showerror("Error",f"Could not parse:\n{ex}",parent=self.root)

def main():
    root=tk.Tk(); root.title("kanban-local"); KanbanApp(root); root.mainloop()

if __name__=="__main__": main()

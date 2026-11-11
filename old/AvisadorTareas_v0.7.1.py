import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import json
import sys
import threading
from pathlib import Path
import winsound

try:
    import pystray
    from PIL import Image
except ImportError:
    pystray = None
    Image = None

APP_NAME = "Avisador de Tareas v0.7.1"
DATA_FILE = Path.home() / "avisador_tareas.json"

COLORS = {
    "bg": "#F4F5F7",
    "card": "#FFFFFF",
    "text": "#202124",
    "muted": "#6B7280",
    "blue": "#1677FF",
    "blue_hover": "#0F66DD",
    "red": "#C62828",
    "green": "#18864B",
    "amber": "#B76A00",
    "line": "#E3E6EA",
    "selection": "#DCEBFF",
}


def resource_path(filename):
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / filename
    return Path(__file__).resolve().parent / filename


ICON_PNG = resource_path("Mantenimiento.png")
ICON_ICO = resource_path("Mantenimiento.ico")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1160x650")
        self.minsize(970, 540)
        self.configure(bg=COLORS["bg"])

        self.tasks = []
        self.triggered = set()
        self.active_alerts = {}
        self.retry_counts = {}
        self.tray_icon = None
        self.tray_thread = None

        self.set_window_icon()
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.bind("<Unmap>", self.on_minimize)
        self.configure_styles()
        self.build_ui()
        self.load_tasks()
        self.refresh()
        self.after(1000, self.check_reminders)

    def configure_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", font=("Segoe UI", 10), background=COLORS["bg"], foreground=COLORS["text"])
        style.configure("Card.TFrame", background=COLORS["card"])
        style.configure("Card.TLabel", background=COLORS["card"], foreground=COLORS["text"])
        style.configure("Muted.TLabel", background=COLORS["card"], foreground=COLORS["muted"], font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI Semibold", 22))
        style.configure("Subtitle.TLabel", background=COLORS["bg"], foreground=COLORS["muted"], font=("Segoe UI", 10))
        style.configure("Primary.TButton", font=("Segoe UI Semibold", 10), padding=(18, 9), background=COLORS["blue"], foreground="white", borderwidth=0)
        style.map("Primary.TButton", background=[("active", COLORS["blue_hover"]), ("pressed", COLORS["blue_hover"])])
        style.configure("Soft.TButton", font=("Segoe UI", 10), padding=(13, 8), background="#EEF1F5", foreground=COLORS["text"], borderwidth=0)
        style.map("Soft.TButton", background=[("active", "#E1E6EC")])
        style.configure("Danger.TButton", font=("Segoe UI", 10), padding=(13, 8), background="#FDEBEC", foreground=COLORS["red"], borderwidth=0)
        style.map("Danger.TButton", background=[("active", "#F9DADC")])
        style.configure("Modern.TEntry", padding=9, fieldbackground="#FAFBFC", bordercolor=COLORS["line"], lightcolor=COLORS["line"], darkcolor=COLORS["line"])
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=38, background=COLORS["card"], fieldbackground=COLORS["card"], foreground=COLORS["text"], borderwidth=0)
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 9), background="#F6F7F9", foreground=COLORS["muted"], padding=(8, 10), borderwidth=0)
        style.map("Treeview", background=[("selected", COLORS["selection"])], foreground=[("selected", COLORS["text"])])

    def set_window_icon(self):
        try:
            if ICON_ICO.exists():
                self.iconbitmap(str(ICON_ICO))
            elif ICON_PNG.exists():
                self._icon_image = tk.PhotoImage(file=str(ICON_PNG))
                self.iconphoto(True, self._icon_image)
        except Exception:
            pass

    def build_ui(self):
        main = ttk.Frame(self, padding=22)
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 16))
        ttk.Label(header, text="Avisador de tareas", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Recordatorios locales, sencillos y sin depender de Outlook", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 0))

        form = ttk.Frame(main, style="Card.TFrame", padding=18)
        form.pack(fill="x", pady=(0, 14))
        fields = [("Tarea", 0), ("Fecha", 1), ("Hora", 2), ("Avisos previos", 3)]
        for label, col in fields:
            ttk.Label(form, text=label, style="Card.TLabel", font=("Segoe UI Semibold", 9)).grid(row=0, column=col, sticky="w", padx=(0, 10))

        self.txt_task = ttk.Entry(form, width=42, style="Modern.TEntry")
        self.txt_date = ttk.Entry(form, width=14, style="Modern.TEntry")
        self.txt_time = ttk.Entry(form, width=9, style="Modern.TEntry")
        self.txt_reminders = ttk.Entry(form, width=20, style="Modern.TEntry")
        entries = [self.txt_task, self.txt_date, self.txt_time, self.txt_reminders]
        for col, entry in enumerate(entries):
            entry.grid(row=1, column=col, sticky="ew", padx=(0, 10), pady=(5, 0))
        ttk.Button(form, text="Añadir tarea", style="Primary.TButton", command=self.add_task).grid(row=1, column=4, sticky="e", pady=(5, 0))
        ttk.Label(form, text="Avisos en minutos separados por comas, por ejemplo 60,30,15,5. Siempre se avisa también a la hora exacta.", style="Muted.TLabel").grid(row=2, column=0, columnspan=5, sticky="w", pady=(10, 0))
        form.columnconfigure(0, weight=1)

        now = datetime.now()
        self.txt_date.insert(0, now.strftime("%d/%m/%Y"))
        self.txt_time.insert(0, (now + timedelta(hours=1)).strftime("%H:%M"))
        self.txt_reminders.insert(0, "15")
        self.txt_task.bind("<Return>", lambda _e: self.add_task())

        # Barra de acciones fija y siempre visible antes del listado.
        actions_card = ttk.Frame(main, style="Card.TFrame", padding=(14, 12))
        actions_card.pack(fill="x", pady=(0, 12))
        ttk.Label(actions_card, text="Acciones de la tarea seleccionada", style="Card.TLabel", font=("Segoe UI Semibold", 9)).pack(side="left", padx=(0, 14))
        for text, command in [
            ("Editar", self.edit_task),
            ("Reprogramar", self.reschedule_task),
            ("Realizada / Pendiente", self.toggle_done),
            ("Prioritaria / Normal", self.toggle_priority),
        ]:
            ttk.Button(actions_card, text=text, style="Soft.TButton", command=command).pack(side="left", padx=(0, 7))
        ttk.Button(actions_card, text="Eliminar", style="Danger.TButton", command=self.delete_task).pack(side="left")
        ttk.Button(actions_card, text="Ocultar", style="Soft.TButton", command=self.hide_to_tray).pack(side="right")

        table_card = ttk.Frame(main, style="Card.TFrame", padding=(1, 1, 1, 1))
        table_card.pack(fill="both", expand=True)
        cols = ("priority", "task", "date", "time", "reminders", "status")
        self.tree = ttk.Treeview(table_card, columns=cols, show="headings", selectmode="browse")
        for key, title in {"priority":"PRIORIDAD", "task":"TAREA", "date":"FECHA", "time":"HORA", "reminders":"AVISOS", "status":"ESTADO"}.items():
            self.tree.heading(key, text=title)
        self.tree.column("priority", width=100, anchor="center", stretch=False)
        self.tree.column("task", width=420)
        self.tree.column("date", width=110, anchor="center", stretch=False)
        self.tree.column("time", width=75, anchor="center", stretch=False)
        self.tree.column("reminders", width=180, anchor="center", stretch=False)
        self.tree.column("status", width=115, anchor="center", stretch=False)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.tag_configure("priority", foreground=COLORS["red"], font=("Segoe UI Semibold", 10))
        self.tree.tag_configure("overdue", foreground=COLORS["red"], font=("Segoe UI Semibold", 10))
        self.tree.tag_configure("done", foreground=COLORS["green"], font=("Segoe UI Semibold", 10))
        self.tree.bind("<Double-1>", lambda _e: self.edit_task())
        self.tree.bind("<Delete>", lambda _e: self.delete_task())


    def parse_dt(self, task):
        return datetime.strptime(task["date"] + " " + task["time"], "%d/%m/%Y %H:%M")

    def parse_reminders(self, value):
        if not value.strip():
            return []
        try:
            values = sorted({int(x.strip()) for x in value.split(",") if x.strip()}, reverse=True)
        except ValueError:
            raise ValueError("Los avisos deben ser minutos separados por comas. Ejemplo: 60,30,15,5")
        if any(x <= 0 or x > 10080 for x in values):
            raise ValueError("Cada aviso debe estar entre 1 y 10080 minutos.")
        return values

    def validate(self, text, date, time, reminders_text="", allow_past=False):
        if not text:
            messagebox.showwarning(APP_NAME, "Escribe la tarea.", parent=self); return None
        try:
            dt = datetime.strptime(date + " " + time, "%d/%m/%Y %H:%M")
            reminders = self.parse_reminders(reminders_text)
        except ValueError as error:
            messagebox.showerror(APP_NAME, str(error), parent=self); return None
        if not allow_past and dt <= datetime.now():
            messagebox.showwarning(APP_NAME, "La fecha y hora deben estar en el futuro.", parent=self); return None
        return dt, reminders

    def add_task(self):
        values = [self.txt_task.get().strip(), self.txt_date.get().strip(), self.txt_time.get().strip(), self.txt_reminders.get().strip()]
        validated = self.validate(*values)
        if validated is None: return
        _, reminders = validated
        self.tasks.append({"id": str(datetime.now().timestamp()), "text": values[0], "date": values[1], "time": values[2], "reminders": reminders, "done": False, "priority": False, "attended": False})
        self.sort_tasks(); self.save_tasks(); self.refresh(); self.txt_task.delete(0, "end"); self.txt_task.focus_set()

    def selected_task(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo(APP_NAME, "Selecciona primero una tarea.", parent=self); return None
        return next((t for t in self.tasks if t["id"] == selection[0]), None)

    def popup_base(self, title, width=460):
        win = tk.Toplevel(self)
        win.title(title); win.configure(bg=COLORS["bg"]); win.resizable(False, False); win.transient(self); win.grab_set()
        try: win.iconbitmap(str(ICON_ICO))
        except Exception: pass
        frame = ttk.Frame(win, style="Card.TFrame", padding=20); frame.pack(fill="both", expand=True, padx=10, pady=10)
        win.update_idletasks(); win.geometry(f"{width}x+{self.winfo_rootx()+180}+{self.winfo_rooty()+120}")
        return win, frame

    def edit_task(self):
        task = self.selected_task()
        if not task: return
        win, frame = self.popup_base("Editar tarea", 510)
        data = [("Tarea", task["text"]), ("Fecha (dd/mm/aaaa)", task["date"]), ("Hora (HH:MM)", task["time"]), ("Avisos previos", ",".join(map(str, task.get("reminders", [15]))))]
        entries=[]
        for row,(label,value) in enumerate(data):
            ttk.Label(frame,text=label,style="Card.TLabel",font=("Segoe UI Semibold",9)).grid(row=row*2,column=0,sticky="w")
            e=ttk.Entry(frame,width=55,style="Modern.TEntry"); e.grid(row=row*2+1,column=0,sticky="ew",pady=(4,10)); e.insert(0,value); entries.append(e)
        def save():
            vals=[e.get().strip() for e in entries]; checked=self.validate(*vals, allow_past=task.get("done",False))
            if checked is None:return
            task.update(text=vals[0],date=vals[1],time=vals[2],reminders=checked[1],attended=False)
            self.clear_task_alert_state(task["id"]); self.sort_tasks(); self.save_tasks(); self.refresh(task["id"]); win.destroy()
        bar=ttk.Frame(frame,style="Card.TFrame");bar.grid(row=8,column=0,sticky="e",pady=(8,0))
        ttk.Button(bar,text="Cancelar",style="Soft.TButton",command=win.destroy).pack(side="right")
        ttk.Button(bar,text="Guardar",style="Primary.TButton",command=save).pack(side="right",padx=(0,8))
        entries[0].focus_set(); entries[0].selection_range(0,"end")

    def reschedule_task(self):
        task = self.selected_task()
        if not task:return
        win, frame = self.popup_base("Reprogramar tarea", 430)
        ttk.Label(frame,text=task["text"],style="Card.TLabel",font=("Segoe UI Semibold",11),wraplength=360).grid(row=0,column=0,columnspan=2,sticky="w",pady=(0,14))
        ttk.Label(frame,text="Nueva fecha",style="Card.TLabel").grid(row=1,column=0,sticky="w")
        ttk.Label(frame,text="Nueva hora",style="Card.TLabel").grid(row=1,column=1,sticky="w",padx=(12,0))
        date=ttk.Entry(frame,width=18,style="Modern.TEntry"); time=ttk.Entry(frame,width=12,style="Modern.TEntry")
        date.grid(row=2,column=0,sticky="w",pady=(5,14)); time.grid(row=2,column=1,sticky="w",padx=(12,0),pady=(5,14))
        date.insert(0,task["date"]);time.insert(0,task["time"])
        def save():
            checked=self.validate(task["text"],date.get().strip(),time.get().strip(),",".join(map(str,task.get("reminders",[]))))
            if checked is None:return
            task.update(date=date.get().strip(),time=time.get().strip(),done=False,attended=False)
            self.clear_task_alert_state(task["id"]);self.sort_tasks();self.save_tasks();self.refresh(task["id"]);win.destroy()
        bar=ttk.Frame(frame,style="Card.TFrame");bar.grid(row=3,column=0,columnspan=2,sticky="e")
        ttk.Button(bar,text="Cancelar",style="Soft.TButton",command=win.destroy).pack(side="right")
        ttk.Button(bar,text="Reprogramar",style="Primary.TButton",command=save).pack(side="right",padx=(0,8));date.focus_set()

    def clear_task_alert_state(self, task_id):
        self.triggered={k for k in self.triggered if not k.startswith(task_id+"_")}
        self.retry_counts={k:v for k,v in self.retry_counts.items() if not k.startswith(task_id+"_")}
        self.close_task_alerts(task_id)

    def toggle_done(self):
        task=self.selected_task()
        if not task:return
        task["done"]=not task.get("done",False); task["attended"]=task["done"]
        if task["done"]: self.close_task_alerts(task["id"])
        self.sort_tasks();self.save_tasks();self.refresh(task["id"])

    def toggle_priority(self):
        task=self.selected_task()
        if not task:return
        task["priority"]=not task.get("priority",False);self.sort_tasks();self.save_tasks();self.refresh(task["id"])

    def delete_task(self):
        task=self.selected_task()
        if not task:return
        if not messagebox.askyesno(APP_NAME,f"¿Eliminar esta tarea?\n\n{task['text']}",parent=self):return
        self.close_task_alerts(task["id"]);self.tasks.remove(task);self.save_tasks();self.refresh()

    def sort_tasks(self):
        self.tasks.sort(key=lambda t:(t.get("done",False),not t.get("priority",False),self.parse_dt(t)))

    def refresh(self, selected=None):
        for row in self.tree.get_children():self.tree.delete(row)
        now=datetime.now()
        for task in self.tasks:
            dt=self.parse_dt(task);done=task.get("done",False)
            unattended=dt<now and not done and not task.get("attended",False)
            if done: status,tag="Realizada","done"
            elif unattended: status,tag="Vencida","overdue"
            else: status,tag="Pendiente","priority" if task.get("priority",False) else ""
            reminders=task.get("reminders",[15]); rtext=", ".join(f"{x} min" for x in reminders) if reminders else "Solo en hora"
            self.tree.insert("","end",iid=task["id"],values=("★ ALTA" if task.get("priority") else "Normal",task["text"],task["date"],task["time"],rtext,status),tags=(tag,) if tag else ())
        if selected and self.tree.exists(selected):self.tree.selection_set(selected);self.tree.focus(selected);self.tree.see(selected)

    def check_reminders(self):
        now=datetime.now();needs_refresh=False
        for task in self.tasks:
            if task.get("done",False):continue
            seconds=(self.parse_dt(task)-now).total_seconds();tid=task["id"]
            for minutes in task.get("reminders",[15]):
                key=f"{tid}_pre_{minutes}"
                if minutes*60-30 < seconds <= minutes*60 and key not in self.triggered:
                    self.triggered.add(key);self.retry_counts[key]=0
                    self.show_alert(task,key,f"Recordatorio · faltan {minutes} minutos",expires=True)
            due_key=f"{tid}_due"
            if -59 < seconds <= 0 and due_key not in self.triggered:
                self.triggered.add(due_key);self.close_task_alerts(tid)
                self.show_alert(task,due_key,"Es la hora",expires=False);needs_refresh=True
        if needs_refresh:self.refresh()
        self.after(1000,self.check_reminders)

    def close_task_alerts(self, task_id):
        for key,win in list(self.active_alerts.items()):
            if key.startswith(task_id+"_"):
                try:win.destroy()
                except tk.TclError:pass
                self.active_alerts.pop(key,None)

    def show_alert(self, task, key, heading, expires):
        if key in self.active_alerts:
            return
        try:winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:pass
        alert=tk.Toplevel(self);self.active_alerts[key]=alert
        alert.title("Recordatorio");alert.configure(bg=COLORS["bg"]);alert.attributes("-topmost",True);alert.resizable(False,False)
        try:alert.iconbitmap(str(ICON_ICO))
        except Exception:pass
        card=ttk.Frame(alert,style="Card.TFrame",padding=24);card.pack(fill="both",expand=True,padx=10,pady=10)
        color=COLORS["red"] if task.get("priority") or not expires else COLORS["blue"]
        tk.Label(card,text=("★ PRIORITARIA\n" if task.get("priority") else "")+heading,font=("Segoe UI Semibold",15),fg=color,bg=COLORS["card"],justify="center").pack(pady=(0,12))
        tk.Label(card,text=task["text"],font=("Segoe UI Semibold",12),fg=COLORS["text"],bg=COLORS["card"],wraplength=480,justify="center").pack(pady=(0,8))
        tk.Label(card,text=f"Programada para las {task['time']}",font=("Segoe UI",10),fg=COLORS["muted"],bg=COLORS["card"]).pack(pady=(0,18))
        def accept():
            task["attended"]=True;self.save_tasks();self.active_alerts.pop(key,None)
            try:alert.destroy()
            except tk.TclError:pass
            self.refresh(task["id"])
        ttk.Button(card,text="Aceptar",style="Primary.TButton",command=accept).pack()
        if expires:
            attempt=self.retry_counts.get(key,0)+1
            tk.Label(card,text=f"Intento {attempt} de 3 · se repetirá si no se atiende",font=("Segoe UI",9),fg=COLORS["muted"],bg=COLORS["card"]).pack(pady=(12,0))
            alert.after(60000,lambda:self.expire_alert(task,key,heading))
        else:
            tk.Label(card,text="Este aviso permanecerá abierto hasta pulsar Aceptar",font=("Segoe UI",9),fg=COLORS["muted"],bg=COLORS["card"]).pack(pady=(12,0))
        alert.protocol("WM_DELETE_WINDOW",accept)
        alert.update_idletasks();w=max(550,alert.winfo_reqwidth());h=max(300,alert.winfo_reqheight())
        alert.geometry(f"{w}x{h}+{self.winfo_screenwidth()-w-35}+{self.winfo_screenheight()-h-80}");alert.focus_force()

    def expire_alert(self, task, key, heading):
        win=self.active_alerts.pop(key,None)
        if win:
            try:win.destroy()
            except tk.TclError:pass
        count=self.retry_counts.get(key,0)+1;self.retry_counts[key]=count
        if count<3 and not task.get("done",False):
            self.after(500,lambda:self.show_alert(task,key,heading,expires=True))

    def load_tasks(self):
        try:
            if DATA_FILE.exists():
                self.tasks=json.loads(DATA_FILE.read_text(encoding="utf-8"))
                for i,t in enumerate(self.tasks):
                    t.setdefault("id",f"{datetime.now().timestamp()}_{i}");t.setdefault("done",False);t.setdefault("priority",False);t.setdefault("reminders",[15]);t.setdefault("attended",False)
                self.sort_tasks()
        except Exception as error:
            self.tasks=[];messagebox.showerror(APP_NAME,f"No se pudieron cargar las tareas:\n\n{error}",parent=self)

    def save_tasks(self):
        try:DATA_FILE.write_text(json.dumps(self.tasks,ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception as error:messagebox.showerror(APP_NAME,f"No se pudieron guardar las tareas:\n\n{error}",parent=self)

    def start_tray(self):
        if pystray is None or Image is None or self.tray_icon is not None:return
        image=Image.open(ICON_PNG).convert("RGBA")
        menu=pystray.Menu(pystray.MenuItem("Abrir Avisador",self.tray_show,default=True),pystray.MenuItem("Salir",self.tray_exit))
        self.tray_icon=pystray.Icon("avisador_tareas",image,APP_NAME,menu);self.tray_thread=threading.Thread(target=self.tray_icon.run,daemon=True);self.tray_thread.start()

    def on_minimize(self,_event=None):
        if self.state()=="iconic":self.after(10,self.hide_to_tray)

    def hide_to_tray(self):
        if pystray is None or Image is None:
            messagebox.showerror(APP_NAME,"Faltan pystray o Pillow.",parent=self);return
        self.withdraw();self.start_tray()

    def tray_show(self,_icon=None,_item=None):self.after(0,self.restore_window)
    def restore_window(self):self.deiconify();self.state("normal");self.lift();self.focus_force()
    def tray_exit(self,_icon=None,_item=None):
        if self.tray_icon:self.tray_icon.stop();self.tray_icon=None
        self.after(0,self.destroy)


if __name__ == "__main__":
    App().mainloop()

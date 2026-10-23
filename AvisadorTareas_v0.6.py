import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont
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

APP_NAME = "Avisador de Tareas v0.6"
DATA_FILE = Path.home() / "avisador_tareas.json"


def resource_path(filename):
    """Devuelve la ruta correcta tanto en Python como dentro del EXE onefile."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / filename
    return Path(__file__).resolve().parent / filename


ICON_PNG = resource_path("Mantenimiento.png")
ICON_ICO = resource_path("Mantenimiento.ico")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1080x590")
        self.minsize(900, 500)
        self.tasks = []
        self.alerted = set()
        self.tray_icon = None
        self.tray_thread = None

        self.set_window_icon()
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.bind("<Unmap>", self.on_minimize)
        self.build_ui()
        self.load_tasks()
        self.refresh()
        self.after(1000, self.check_reminders)

    def set_window_icon(self):
        try:
            if ICON_ICO.exists():
                self.iconbitmap(str(ICON_ICO))
            elif ICON_PNG.exists():
                self._icon_image = tk.PhotoImage(file=str(ICON_PNG))
                self.iconphoto(True, self._icon_image)
        except Exception:
            pass

    def load_tray_image(self):
        if Image is None or not ICON_PNG.exists():
            return None
        return Image.open(ICON_PNG).convert("RGBA")

    def start_tray(self):
        if pystray is None or self.tray_icon is not None:
            return
        image = self.load_tray_image()
        if image is None:
            return
        menu = pystray.Menu(
            pystray.MenuItem("Abrir Avisador", self.tray_show, default=True),
            pystray.MenuItem("Salir", self.tray_exit),
        )
        self.tray_icon = pystray.Icon("avisador_tareas", image, APP_NAME, menu)
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def on_minimize(self, _event=None):
        if self.state() == "iconic":
            self.after(10, self.hide_to_tray)

    def hide_to_tray(self):
        if pystray is None or Image is None:
            messagebox.showerror(
                APP_NAME,
                "Faltan dependencias para el icono junto al reloj.\n\n"
                "Ejecuta Instalar_Avisador_v0.5.bat.",
                parent=self,
            )
            return
        if not ICON_PNG.exists():
            messagebox.showerror(APP_NAME, "El recurso interno del icono no está disponible. Vuelve a generar el EXE con Crear_EXE_Avisador_v0.6.bat.", parent=self)
            return
        self.withdraw()
        self.start_tray()

    def tray_show(self, _icon=None, _item=None):
        self.after(0, self.restore_window)

    def restore_window(self):
        self.deiconify()
        self.state("normal")
        self.lift()
        self.focus_force()

    def tray_exit(self, _icon=None, _item=None):
        if self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None
        self.after(0, self.destroy)

    def build_ui(self):
        style = ttk.Style(self)
        style.configure("Treeview", rowheight=29)

        top = ttk.LabelFrame(self, text="Nueva tarea", padding=12)
        top.pack(fill="x", padx=12, pady=(12, 8))

        labels = ["Tarea", "Fecha (dd/mm/aaaa)", "Hora (HH:MM)", "Avisos previos (minutos)"]
        for col, text in enumerate(labels):
            ttk.Label(top, text=text).grid(row=0, column=col, sticky="w")

        self.txt_task = ttk.Entry(top, width=42)
        self.txt_date = ttk.Entry(top, width=16)
        self.txt_time = ttk.Entry(top, width=10)
        self.txt_reminders = ttk.Entry(top, width=23)
        self.txt_task.grid(row=1, column=0, padx=(0, 8), sticky="ew")
        self.txt_date.grid(row=1, column=1, padx=(0, 8))
        self.txt_time.grid(row=1, column=2, padx=(0, 8))
        self.txt_reminders.grid(row=1, column=3, padx=(0, 8))
        ttk.Button(top, text="Añadir tarea", command=self.add_task).grid(row=1, column=4)
        top.columnconfigure(0, weight=1)

        now = datetime.now()
        self.txt_date.insert(0, now.strftime("%d/%m/%Y"))
        self.txt_time.insert(0, (now + timedelta(hours=1)).strftime("%H:%M"))
        self.txt_reminders.insert(0, "15")
        self.txt_task.bind("<Return>", lambda _event: self.add_task())

        ttk.Label(
            top,
            text="Ejemplo: 60,30,15,5. Siempre avisa también a la hora exacta. Si no quieres avisos previos, deja el campo vacío.",
            foreground="#555555",
        ).grid(row=2, column=0, columnspan=5, sticky="w", pady=(8, 0))

        mid = ttk.Frame(self, padding=(12, 2, 12, 8))
        mid.pack(fill="both", expand=True)
        cols = ("priority", "task", "date", "time", "reminders", "status")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="browse")
        headings = {
            "priority": "Prioridad", "task": "Tarea", "date": "Fecha", "time": "Hora",
            "reminders": "Avisos previos", "status": "Estado"
        }
        for key, text in headings.items():
            self.tree.heading(key, text=text)
        self.tree.column("priority", width=90, anchor="center", stretch=False)
        self.tree.column("task", width=390)
        self.tree.column("date", width=110, anchor="center", stretch=False)
        self.tree.column("time", width=70, anchor="center", stretch=False)
        self.tree.column("reminders", width=170, anchor="center", stretch=False)
        self.tree.column("status", width=100, anchor="center", stretch=False)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)

        bold_font = tkfont.Font(family="Segoe UI", size=9, weight="bold")
        self.tree.tag_configure("priority", foreground="#b00020", font=bold_font)
        self.tree.tag_configure("done", foreground="#777777")
        self.tree.tag_configure("overdue", foreground="#c05a00")
        self.tree.bind("<Double-1>", lambda _event: self.edit_task())
        self.tree.bind("<Delete>", lambda _event: self.delete_task())

        buttons = ttk.Frame(self, padding=(12, 0, 12, 8))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Editar", command=self.edit_task).pack(side="left")
        ttk.Button(buttons, text="Realizada / Pendiente", command=self.toggle_done).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Prioritaria / Normal", command=self.toggle_priority).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Eliminar", command=self.delete_task).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Ocultar junto al reloj", command=self.hide_to_tray).pack(side="right")
        ttk.Button(
            buttons, text="Probar aviso",
            command=lambda: self.show_alert("AVISO DE PRUEBA", "Este es un aviso de prueba.", True)
        ).pack(side="right", padx=(0, 8))

        ttk.Label(
            self,
            text="Al minimizar o cerrar, el programa continúa junto al reloj y sigue mostrando los avisos.",
            padding=(12, 4, 12, 12),
        ).pack(fill="x")

    def parse_dt(self, task):
        return datetime.strptime(task["date"] + " " + task["time"], "%d/%m/%Y %H:%M")

    def parse_reminders(self, value):
        value = value.strip()
        if not value:
            return []
        try:
            values = sorted({int(x.strip()) for x in value.split(",") if x.strip()}, reverse=True)
        except ValueError:
            raise ValueError("Los avisos deben ser minutos separados por comas. Ejemplo: 60,30,15,5")
        if any(x <= 0 or x > 10080 for x in values):
            raise ValueError("Cada aviso debe estar entre 1 y 10080 minutos (7 días).")
        return values

    def validate_values(self, text, date, time, reminders_text, allow_past=False):
        if not text:
            messagebox.showwarning(APP_NAME, "Escribe la tarea.", parent=self)
            return None
        try:
            dt = datetime.strptime(date + " " + time, "%d/%m/%Y %H:%M")
            reminders = self.parse_reminders(reminders_text)
        except ValueError as error:
            messagebox.showerror(APP_NAME, str(error), parent=self)
            return None
        if not allow_past and dt <= datetime.now():
            messagebox.showwarning(APP_NAME, "La fecha y hora deben estar en el futuro.", parent=self)
            return None
        return dt, reminders

    def add_task(self):
        text = self.txt_task.get().strip()
        date = self.txt_date.get().strip()
        time = self.txt_time.get().strip()
        reminders_text = self.txt_reminders.get().strip()
        validated = self.validate_values(text, date, time, reminders_text)
        if validated is None:
            return
        _, reminders = validated
        self.tasks.append({
            "id": str(datetime.now().timestamp()), "text": text, "date": date, "time": time,
            "done": False, "priority": False, "reminders": reminders,
        })
        self.sort_tasks()
        self.save_tasks()
        self.refresh()
        self.txt_task.delete(0, "end")
        self.txt_task.focus_set()

    def selected_task(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo(APP_NAME, "Selecciona primero una tarea.", parent=self)
            return None
        return next((task for task in self.tasks if task["id"] == selection[0]), None)

    def edit_task(self):
        task = self.selected_task()
        if task is None:
            return
        window = tk.Toplevel(self)
        window.title("Editar tarea")
        window.resizable(False, False)
        window.transient(self)
        window.grab_set()
        try:
            if ICON_ICO.exists():
                window.iconbitmap(str(ICON_ICO))
        except Exception:
            pass
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill="both", expand=True)

        fields = [("Tarea", task["text"], 55), ("Fecha (dd/mm/aaaa)", task["date"], 20),
                  ("Hora (HH:MM)", task["time"], 15),
                  ("Avisos previos en minutos", ",".join(map(str, task.get("reminders", [15]))), 30)]
        entries = []
        for row, (label, value, width) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row * 2, column=0, sticky="w")
            entry = ttk.Entry(frame, width=width)
            entry.grid(row=row * 2 + 1, column=0, sticky="ew", pady=(0, 9))
            entry.insert(0, value)
            entries.append(entry)

        def save_edit():
            text, date, time, reminders_text = [entry.get().strip() for entry in entries]
            validated = self.validate_values(text, date, time, reminders_text, task.get("done", False))
            if validated is None:
                return
            _, reminders = validated
            task.update(text=text, date=date, time=time, reminders=reminders)
            self.alerted = {key for key in self.alerted if not key.startswith(task["id"] + "_")}
            self.sort_tasks()
            self.save_tasks()
            self.refresh(task["id"])
            window.destroy()

        actions = ttk.Frame(frame)
        actions.grid(row=8, column=0, sticky="e", pady=(8, 0))
        ttk.Button(actions, text="Cancelar", command=window.destroy).pack(side="right")
        ttk.Button(actions, text="Guardar cambios", command=save_edit).pack(side="right", padx=(0, 8))
        window.bind("<Return>", lambda _event: save_edit())
        window.bind("<Escape>", lambda _event: window.destroy())
        entries[0].focus_set()
        entries[0].selection_range(0, "end")

    def toggle_done(self):
        task = self.selected_task()
        if task is None:
            return
        task["done"] = not task.get("done", False)
        self.sort_tasks(); self.save_tasks(); self.refresh(task["id"])

    def toggle_priority(self):
        task = self.selected_task()
        if task is None:
            return
        task["priority"] = not task.get("priority", False)
        self.sort_tasks(); self.save_tasks(); self.refresh(task["id"])

    def delete_task(self):
        task = self.selected_task()
        if task is None:
            return
        if not messagebox.askyesno(APP_NAME, f"¿Eliminar esta tarea?\n\n{task['text']}", icon="warning", parent=self):
            return
        self.tasks.remove(task)
        self.alerted = {key for key in self.alerted if not key.startswith(task["id"] + "_")}
        self.save_tasks(); self.refresh()

    def sort_tasks(self):
        self.tasks.sort(key=lambda task: (task.get("done", False), not task.get("priority", False), self.parse_dt(task)))

    def refresh(self, select_id=None):
        for item in self.tree.get_children():
            self.tree.delete(item)
        now = datetime.now()
        for task in self.tasks:
            done = task.get("done", False)
            priority = task.get("priority", False)
            if done:
                status, tag = "Realizada", "done"
            elif self.parse_dt(task) < now:
                status, tag = "Vencida", "priority" if priority else "overdue"
            else:
                status, tag = "Pendiente", "priority" if priority else ""
            reminders = task.get("reminders", [15])
            reminder_text = ", ".join(f"{x} min" for x in reminders) if reminders else "Solo hora exacta"
            self.tree.insert("", "end", iid=task["id"],
                             values=("★ ALTA" if priority else "Normal", task["text"], task["date"],
                                     task["time"], reminder_text, status),
                             tags=(tag,) if tag else ())
        if select_id and self.tree.exists(select_id):
            self.tree.selection_set(select_id); self.tree.focus(select_id); self.tree.see(select_id)

    def check_reminders(self):
        now = datetime.now()
        for task in self.tasks:
            if task.get("done", False):
                continue
            dt = self.parse_dt(task)
            seconds = (dt - now).total_seconds()
            priority = task.get("priority", False)

            for minutes in task.get("reminders", [15]):
                target_seconds = minutes * 60
                key = f"{task['id']}_pre_{minutes}"
                if target_seconds - 30 < seconds <= target_seconds and key not in self.alerted:
                    self.alerted.add(key)
                    self.show_alert(
                        f"RECORDATORIO: FALTAN {minutes} MINUTOS",
                        f"{task['text']}\n\nHora: {task['time']}", priority
                    )

            due_key = task["id"] + "_due"
            if -59 < seconds <= 0 and due_key not in self.alerted:
                self.alerted.add(due_key)
                self.show_alert("¡ES LA HORA!", f"{task['text']}\n\nHora: {task['time']}", priority)

        self.after(1000, self.check_reminders)

    def show_alert(self, title, text, priority=False):
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass
        alert = tk.Toplevel(self)
        alert.title("Recordatorio")
        alert.resizable(False, False)
        alert.attributes("-topmost", True)
        try:
            if ICON_ICO.exists():
                alert.iconbitmap(str(ICON_ICO))
        except Exception:
            pass
        frame = ttk.Frame(alert, padding=22)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text=("★ PRIORITARIA ★\n" if priority else "") + title,
                 font=("Segoe UI", 14, "bold"), fg="#b00020" if priority else "#1f4e79",
                 justify="center").pack(pady=(0, 14))
        tk.Label(frame, text=text, font=("Segoe UI", 12, "bold"), justify="center",
                 wraplength=480).pack(padx=12, pady=(0, 18))
        ttk.Button(alert, text="Aceptar", command=alert.destroy).pack(pady=(0, 18))
        alert.bind("<Return>", lambda _event: alert.destroy())
        alert.bind("<Escape>", lambda _event: alert.destroy())
        alert.update_idletasks()
        width, height = max(520, alert.winfo_reqwidth()), max(250, alert.winfo_reqheight())
        x, y = self.winfo_screenwidth() - width - 35, self.winfo_screenheight() - height - 80
        alert.geometry(f"{width}x{height}+{x}+{y}")
        alert.focus_force()

    def load_tasks(self):
        try:
            if DATA_FILE.exists():
                self.tasks = json.loads(DATA_FILE.read_text(encoding="utf-8"))
                for index, task in enumerate(self.tasks):
                    task.setdefault("id", f"{datetime.now().timestamp()}_{index}")
                    task.setdefault("done", False)
                    task.setdefault("priority", False)
                    task.setdefault("reminders", [15])
                self.sort_tasks()
        except Exception as error:
            self.tasks = []
            messagebox.showerror(APP_NAME, f"No se pudieron cargar las tareas:\n\n{error}", parent=self)

    def save_tasks(self):
        try:
            DATA_FILE.write_text(json.dumps(self.tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as error:
            messagebox.showerror(APP_NAME, f"No se pudieron guardar las tareas:\n\n{error}", parent=self)


if __name__ == "__main__":
    App().mainloop()

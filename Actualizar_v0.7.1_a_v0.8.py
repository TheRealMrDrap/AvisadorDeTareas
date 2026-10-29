from pathlib import Path

base = Path(__file__).resolve().parent
src = base / "AvisadorTareas_v0.7.1.py"
dst = base / "AvisadorTareas_v0.8.py"
if not src.exists():
    raise SystemExit("ERROR: falta AvisadorTareas_v0.7.1.py en esta carpeta.")
s = src.read_text(encoding="utf-8")
s = s.replace('APP_NAME = "Avisador de Tareas v0.7.1"', 'APP_NAME = "Avisador de Tareas v0.8"')
start = s.find('    def popup_base(self, title, width=460):')
end = s.find('\n    def edit_task(self):', start)
if start < 0 or end < 0:
    raise SystemExit("ERROR: no encuentro popup_base de la v0.7.1.")
new = '''    def popup_base(self, title, width=520, height=420):
        win = tk.Toplevel(self)
        win.title(title)
        win.configure(bg=COLORS["bg"])
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        try:
            win.iconbitmap(str(ICON_ICO))
        except Exception:
            pass

        frame = ttk.Frame(win, style="Card.TFrame", padding=24)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        self.update_idletasks()
        x = max(0, self.winfo_rootx() + (self.winfo_width() - width) // 2)
        y = max(0, self.winfo_rooty() + (self.winfo_height() - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.minsize(width, height)
        win.maxsize(width, height)
        win.lift()
        win.focus_force()
        return win, frame
'''
s = s[:start] + new + s[end:]
s = s.replace('self.popup_base("Editar tarea", 510)', 'self.popup_base("Editar tarea", 560, 470)')
s = s.replace('self.popup_base("Reprogramar tarea", 430)', 'self.popup_base("Reprogramar tarea", 480, 280)')
s = s.replace('        data = [("Tarea", task["text"]),', '        frame.columnconfigure(0, weight=1)\n        data = [("Tarea", task["text"]),', 1)
compile(s, str(dst), "exec")
dst.write_text(s, encoding="utf-8")
print("CORRECTO: creado AvisadorTareas_v0.8.py")

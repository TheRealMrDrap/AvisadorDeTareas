from pathlib import Path

src = Path(__file__).with_name("AvisadorTareas_v0.7.py")
dst = Path(__file__).with_name("AvisadorTareas_v0.7.1.py")
if not src.exists():
    raise SystemExit("ERROR: deja AvisadorTareas_v0.7.py en esta misma carpeta.")
s = src.read_text(encoding="utf-8")
s = s.replace('APP_NAME = "Avisador de Tareas v0.7"', 'APP_NAME = "Avisador de Tareas v0.7.1"')
s = s.replace('self.geometry("1160x680")', 'self.geometry("1160x650")')
s = s.replace('self.minsize(970, 570)', 'self.minsize(970, 540)')
old = '''        actions = ttk.Frame(main)
        actions.pack(fill="x", pady=(14, 0))
        for text, command in [("Editar", self.edit_task), ("Reprogramar", self.reschedule_task), ("Realizada / Pendiente", self.toggle_done), ("Prioritaria / Normal", self.toggle_priority)]:
            ttk.Button(actions, text=text, style="Soft.TButton", command=command).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Eliminar", style="Danger.TButton", command=self.delete_task).pack(side="left")
        ttk.Button(actions, text="Ocultar junto al reloj", style="Soft.TButton", command=self.hide_to_tray).pack(side="right")
'''
if old not in s:
    raise SystemExit("ERROR: no reconozco esta copia de la v0.7 o ya esta corregida.")
s = s.replace(old, "")
marker = '        table_card = ttk.Frame(main, style="Card.TFrame", padding=(1, 1, 1, 1))\n'
bar = '''        # Barra de acciones fija y siempre visible antes del listado.
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

'''
if marker not in s:
    raise SystemExit("ERROR: no encuentro el listado de tareas.")
s = s.replace(marker, bar + marker, 1)
dst.write_text(s, encoding="utf-8")
print(f"CORRECTO: creado {dst.name}")

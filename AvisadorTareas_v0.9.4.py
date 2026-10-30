import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import json, sys, threading, os, time, tempfile
from pathlib import Path
import winsound

try:
    import pystray
    from PIL import Image
except ImportError:
    pystray = None
    Image = None

APP_NAME = "Avisador de Tareas v0.9.4"
LOCAL_DATA_FILE = Path.home() / "avisador_tareas.json"
CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "AvisadorTareas"
CONFIG_FILE = CONFIG_DIR / "config.json"
COLORS={"bg":"#F3F5F8","card":"#FFFFFF","text":"#202124","muted":"#6B7280","blue":"#1677FF","blue2":"#0F66DD","red":"#C62828","green":"#18864B","line":"#E3E6EA","select":"#DCEBFF"}

def resource_path(name):
    if getattr(sys,"frozen",False) and hasattr(sys,"_MEIPASS"): return Path(sys._MEIPASS)/name
    return Path(__file__).resolve().parent/name
ICON_PNG=resource_path("AvisadorTareas_Icono_512.png")
ICON_ICO=resource_path("Mantenimiento.ico")

class RoundedButton(tk.Canvas):
    """Botón redondeado antialias. Hover/click solo cambian color: nunca geometría."""
    def __init__(self,parent,text,command,bg="#EEF1F5",fg="#202124",hover="#E1E6EC",width=150,height=38,radius=16,font=("Segoe UI Variable Text",10,"bold")):
        super().__init__(parent,width=width,height=height,bg=parent.cget("bg"),highlightthickness=0,bd=0,cursor="hand2")
        self._text=text; self.command=command; self.normal=bg; self.hover=hover; self.fg=fg
        self.btnw=width; self.btnh=height; self.radius=radius; self.font=font; self._photo=None
        self.bind("<Enter>",lambda e:self.draw(self.hover))
        self.bind("<Leave>",lambda e:self.draw(self.normal))
        self.bind("<Button-1>",lambda e:self.draw(self.hover))
        self.bind("<ButtonRelease-1>",self.click)
        self.draw(self.normal)
    def draw(self,color):
        self.delete("all")
        try:
            from PIL import Image as PILImage, ImageDraw, ImageTk
            scale=4; w=self.btnw*scale; h=self.btnh*scale; r=self.radius*scale
            img=PILImage.new("RGBA",(w,h),(0,0,0,0)); d=ImageDraw.Draw(img)
            # Sombra fija y cuerpo fijo. No cambia ninguna coordenada entre estados.
            d.rounded_rectangle((4*scale,4*scale,(self.btnw-2)*scale,(self.btnh-1)*scale),radius=r,fill="#D9DEE5")
            d.rounded_rectangle((1*scale,1*scale,(self.btnw-3)*scale,(self.btnh-4)*scale),radius=r,fill=color)
            img=img.resize((self.btnw,self.btnh),PILImage.Resampling.LANCZOS)
            self._photo=ImageTk.PhotoImage(img); self.create_image(0,0,image=self._photo,anchor="nw")
        except Exception:
            self.create_rectangle(1,1,self.btnw-3,self.btnh-4,fill=color,outline="")
        self.create_text(self.btnw/2-1,self.btnh/2-2,text=self._text,fill=self.fg,font=self.font)
    def click(self,e):
        self.draw(self.hover)
        if self.command:self.command()
    def set_text(self,t): self._text=t; self.draw(self.normal)

class App(tk.Tk):
    def __init__(self):
        super().__init__();self.title(APP_NAME);self.geometry("1180x690");self.minsize(1000,580);self.configure(bg=COLORS["bg"])
        self.tasks=[];self.triggered=set();self.active_alerts={};self.retry_counts={};self.tray_icon=None;self.tray_thread=None
        self.config_data=self.load_config();self.data_file=self.resolve_data_file();self.last_data_signature=None;self.reloading=False
        self.set_icon();self.protocol("WM_DELETE_WINDOW",self.hide_to_tray);self.bind("<Unmap>",self.on_minimize)
        self.styles();self.build_ui();self.load_tasks();self.migrate_history();self.refresh();self.after(1000,self.check_reminders);self.after(3000,self.auto_reload_tasks);self.after(60000,self.history_tick)
    def set_icon(self):
        try:self.iconbitmap(str(ICON_ICO))
        except Exception:pass
    def styles(self):
        st=ttk.Style(self)
        try:st.theme_use("clam")
        except:pass
        st.configure(".",font=("Segoe UI Variable Text",10),background=COLORS["bg"],foreground=COLORS["text"])
        st.configure("Title.TLabel",font=("Segoe UI Variable Display",22,"bold"),background=COLORS["bg"]);st.configure("Sub.TLabel",font=("Segoe UI Variable Text",10),background=COLORS["bg"],foreground=COLORS["muted"])
        st.configure("Modern.TEntry",padding=9,fieldbackground="#FAFBFC",bordercolor=COLORS["line"])
        st.configure("Treeview",font=("Segoe UI Variable Text",10),rowheight=38,background="white",fieldbackground="white",borderwidth=0)
        st.configure("Treeview.Heading",font=("Segoe UI Variable Text",9,"bold"),background="#F6F7F9",foreground=COLORS["muted"],padding=(8,10),borderwidth=0)
        st.map("Treeview",background=[("selected",COLORS["select"])],foreground=[("selected",COLORS["text"])])

    def build_ui(self):
        main=tk.Frame(self,bg=COLORS["bg"]);main.pack(fill="both",expand=True,padx=22,pady=18)
        header=tk.Frame(main,bg=COLORS["bg"]);header.pack(fill="x")
        left=tk.Frame(header,bg=COLORS["bg"]);left.pack(side="left",fill="x",expand=True)
        tk.Label(left,text="Avisador de tareas",font=("Segoe UI Variable Display",22,"bold"),bg=COLORS["bg"],fg=COLORS["text"]).pack(anchor="w")
        tk.Label(left,text="Recordatorios locales, rápidos y sin depender de Outlook",font=("Segoe UI Variable Text",10),bg=COLORS["bg"],fg=COLORS["muted"]).pack(anchor="w",pady=(2,14))
        right=tk.Frame(header,bg=COLORS["bg"]);right.pack(side="right",anchor="ne")
        tk.Label(right,text="Técnico",font=("Segoe UI Variable Text",9,"bold"),bg=COLORS["bg"],fg=COLORS["muted"]).pack(side="left",padx=(0,6))
        self.tech_var=tk.StringVar(value=self.config_data.get("last_technician", ""))
        self.tech_combo=ttk.Combobox(right,textvariable=self.tech_var,values=self.config_data.get("technicians",[]),width=20)
        self.tech_combo.pack(side="left",padx=(0,8));self.tech_combo.bind("<<ComboboxSelected>>",self.save_current_technician);self.tech_combo.bind("<FocusOut>",self.save_current_technician)
        RoundedButton(right,"Opciones",self.show_options,width=95,height=34).pack(side="left")
        form=tk.Frame(main,bg="white",highlightthickness=1,highlightbackground=COLORS["line"]);form.pack(fill="x",pady=(0,12));inner=tk.Frame(form,bg="white");inner.pack(fill="x",padx=17,pady=14)
        for c,t in enumerate(["Tarea","Fecha","Hora","Avisos previos"]):tk.Label(inner,text=t,font=("Segoe UI Variable Text",9,"bold"),bg="white",fg=COLORS["text"]).grid(row=0,column=c,sticky="w")
        self.txt_task=ttk.Entry(inner,style="Modern.TEntry");self.txt_date=ttk.Entry(inner,width=14,style="Modern.TEntry");self.txt_time=ttk.Entry(inner,width=9,style="Modern.TEntry");self.txt_reminders=ttk.Entry(inner,width=19,style="Modern.TEntry")
        for c,e in enumerate([self.txt_task,self.txt_date,self.txt_time,self.txt_reminders]):e.grid(row=1,column=c,sticky="ew",padx=(0,10),pady=(5,0))
        addwrap=tk.Frame(inner,bg="white");addwrap.grid(row=1,column=4,sticky="e",pady=(5,0));RoundedButton(addwrap,"Añadir tarea",self.add_task,bg=COLORS["blue"],fg="white",hover=COLORS["blue2"],width=132).pack()
        inner.columnconfigure(0,weight=1);now=datetime.now();self.txt_date.insert(0,now.strftime("%d/%m/%Y"));self.txt_time.insert(0,(now+timedelta(hours=1)).strftime("%H:%M"));self.txt_reminders.insert(0,"15")
        tk.Label(inner,text="Ejemplo: 60,30,15,5. Siempre se avisa también a la hora exacta.",font=("Segoe UI Variable Text",9),bg="white",fg=COLORS["muted"]).grid(row=2,column=0,columnspan=5,sticky="w",pady=(8,0))
        actions=tk.Frame(main,bg="white",highlightthickness=1,highlightbackground=COLORS["line"]);actions.pack(fill="x",pady=(0,12));aw=tk.Frame(actions,bg="white");aw.pack(fill="x",padx=13,pady=9)
        for text,cmd,w in [("Editar",self.edit_task,92),("Reprogramar",self.reschedule_task,125),("Realizada / Pendiente",self.toggle_done,176),("Prioritaria / Normal",self.toggle_priority,165)]:RoundedButton(aw,text,cmd,width=w).pack(side="left",padx=(0,7))
        RoundedButton(aw,"Eliminar",self.delete_task,bg="#FCE8E8",fg=COLORS["red"],hover="#F7D4D4",width=95).pack(side="left")
        RoundedButton(aw,"Ocultar",self.hide_to_tray,width=95).pack(side="right")
        # Pestañas propias: dimensiones idénticas siempre. Solo cambia color/fondo al seleccionar.
        self.tabbar=tk.Frame(main,bg=COLORS["bg"],height=45);self.tabbar.pack(fill="x");self.tabbar.pack_propagate(False)
        self.pending_tab_btn=tk.Label(self.tabbar,text="Pendientes (0)",width=18,height=2,font=("Segoe UI Variable Text",10,"bold"),cursor="hand2",bd=0)
        self.history_tab_btn=tk.Label(self.tabbar,text="Histórico (0)",width=18,height=2,font=("Segoe UI Variable Text",10,"bold"),cursor="hand2",bd=0)
        self.pending_tab_btn.pack(side="left",padx=(0,4));self.history_tab_btn.pack(side="left")
        self.pending_tab_btn.bind("<Button-1>",lambda e:self.select_tab("pending"));self.history_tab_btn.bind("<Button-1>",lambda e:self.select_tab("history"))
        self.tabarea=tk.Frame(main,bg="white",highlightthickness=1,highlightbackground=COLORS["line"]);self.tabarea.pack(fill="both",expand=True)
        self.pending_tab=tk.Frame(self.tabarea,bg="white");self.history_tab=tk.Frame(self.tabarea,bg="white")
        for f in (self.pending_tab,self.history_tab):f.place(x=0,y=0,relwidth=1,relheight=1)
        self.active_tab="pending";self.select_tab("pending")
        self.tree=self.make_tree(self.pending_tab,history=False);self.history_tree=self.make_tree(self.history_tab,history=True)
        self.tree.bind("<Double-1>",lambda e:self.edit_task());self.tree.bind("<Delete>",lambda e:self.delete_task());self.tree.bind("<Button-3>",self.show_pending_context)
        self.history_tree.bind("<Double-1>",lambda e:self.restore_history());self.history_tree.bind("<Button-3>",self.show_history_context)
        hb=tk.Frame(self.history_tab,bg="white");hb.pack(fill="x",padx=10,pady=8);RoundedButton(hb,"Restaurar",self.restore_history,width=105).pack(side="left");RoundedButton(hb,"Eliminar histórico",self.delete_history,bg="#FCE8E8",fg=COLORS["red"],hover="#F7D4D4",width=150).pack(side="left",padx=7)
    def select_tab(self,name):
        self.active_tab=name
        if name=="history": self.history_tab.tkraise()
        else: self.pending_tab.tkraise()
        active_bg="#FFFFFF"; inactive_bg="#E3E8EF"
        for key,btn in (("pending",self.pending_tab_btn),("history",self.history_tab_btn)):
            active=(key==name);btn.configure(bg=active_bg if active else inactive_bg,fg=COLORS["blue"] if active else COLORS["text"])

    def make_tree(self,parent,history=False):
        wrap=tk.Frame(parent,bg="white");wrap.pack(fill="both",expand=True)
        cols=("priority","task","date","time","reminders","status") if not history else ("task","completed","date","time")
        tr=ttk.Treeview(wrap,columns=cols,show="headings",selectmode="browse")
        titles={"priority":"PRIORIDAD","task":"TAREA","date":"FECHA","time":"HORA","reminders":"AVISOS","status":"ESTADO","completed":"REALIZADA EL"}
        for c in cols:tr.heading(c,text=titles[c])
        if history:
            tr.column("task",width=520);tr.column("completed",width=200,anchor="center");tr.column("date",width=130,anchor="center");tr.column("time",width=90,anchor="center")
        else:
            tr.column("priority",width=100,anchor="center");tr.column("task",width=420);tr.column("date",width=110,anchor="center");tr.column("time",width=75,anchor="center");tr.column("reminders",width=170,anchor="center");tr.column("status",width=110,anchor="center")
        tr.tag_configure("overdue",foreground=COLORS["red"],font=("Segoe UI Variable Text",10,"bold"));tr.tag_configure("done",foreground=COLORS["green"],font=("Segoe UI Variable Text",10,"bold"));tr.tag_configure("priority",foreground=COLORS["red"],font=("Segoe UI Variable Text",10,"bold"));tr.tag_configure("history",foreground="#59636F")
        tr.pack(side="left",fill="both",expand=True);sb=ttk.Scrollbar(wrap,orient="vertical",command=tr.yview);sb.pack(side="right",fill="y");tr.configure(yscrollcommand=sb.set);return tr
    def parse_dt(self,t):return datetime.strptime(t["date"]+" "+t["time"],"%d/%m/%Y %H:%M")
    def parse_reminders(self,v):
        if not v.strip():return []
        try:vals=sorted({int(x.strip()) for x in v.split(",") if x.strip()},reverse=True)
        except:raise ValueError("Los avisos deben ser minutos separados por comas.")
        if any(x<=0 or x>10080 for x in vals):raise ValueError("Cada aviso debe estar entre 1 y 10080 minutos.")
        return vals
    def validate(self,text,date,time,rems,allow_past=False):
        if not text:messagebox.showwarning(APP_NAME,"Escribe la tarea.",parent=self);return None
        try:dt=datetime.strptime(date+" "+time,"%d/%m/%Y %H:%M");rr=self.parse_reminders(rems)
        except ValueError as e:messagebox.showerror(APP_NAME,str(e),parent=self);return None
        if not allow_past and dt<=datetime.now():messagebox.showwarning(APP_NAME,"La fecha y hora deben estar en el futuro.",parent=self);return None
        return dt,rr
    def add_task(self):
        v=[self.txt_task.get().strip(),self.txt_date.get().strip(),self.txt_time.get().strip(),self.txt_reminders.get().strip()];ok=self.validate(*v)
        if not ok:return
        self.tasks.append({"id":str(datetime.now().timestamp()),"text":v[0],"date":v[1],"time":v[2],"reminders":ok[1],"done":False,"priority":False,"attended":False,"completed_at":None,"archived":False,"technician":self.tech_var.get().strip()});self.save_tasks();self.refresh();self.txt_task.delete(0,"end")
    def selected_task(self):
        sel=self.tree.selection()
        if not sel:messagebox.showinfo(APP_NAME,"Selecciona primero una tarea pendiente.",parent=self);return None
        return next((t for t in self.tasks if t["id"]==sel[0]),None)
    def popup(self,title,w,h):
        win=tk.Toplevel(self);win.title(title);win.configure(bg=COLORS["bg"]);win.resizable(False,False);win.transient(self);win.grab_set()
        try:win.iconbitmap(str(ICON_ICO))
        except:pass
        card=tk.Frame(win,bg="white",highlightthickness=1,highlightbackground=COLORS["line"]);card.pack(fill="both",expand=True,padx=12,pady=12);self.update_idletasks();x=max(0,self.winfo_rootx()+(self.winfo_width()-w)//2);y=max(0,self.winfo_rooty()+(self.winfo_height()-h)//2);win.geometry(f"{w}x{h}+{x}+{y}");win.lift();win.focus_force();return win,card
    def edit_task(self):
        t=self.selected_task()
        if not t:return
        win,card=self.popup("Editar tarea",570,500);box=tk.Frame(card,bg="white");box.pack(fill="both",expand=True,padx=22,pady=20);entries=[]
        data=[("Tarea",t["text"]),("Fecha (dd/mm/aaaa)",t["date"]),("Hora (HH:MM)",t["time"]),("Avisos previos",",".join(map(str,t.get("reminders",[15]))))]
        for label,val in data:tk.Label(box,text=label,font=("Segoe UI Variable Text",9,"bold"),bg="white").pack(anchor="w");e=ttk.Entry(box,style="Modern.TEntry");e.pack(fill="x",pady=(4,10));e.insert(0,val);entries.append(e)
        def save():
            v=[e.get().strip() for e in entries];ok=self.validate(*v,allow_past=t.get("done",False))
            if not ok:return
            t.update(text=v[0],date=v[1],time=v[2],reminders=ok[1],attended=False);self.clear_alert_state(t["id"]);self.save_tasks();self.refresh();win.destroy()
        bar=tk.Frame(box,bg="white");bar.pack(fill="x",pady=(5,0));RoundedButton(bar,"Guardar",save,bg=COLORS["blue"],fg="white",hover=COLORS["blue2"],width=110).pack(side="right");RoundedButton(bar,"Cancelar",win.destroy,width=100).pack(side="right",padx=7)
    def reschedule_task(self):
        t=self.selected_task()
        if not t:return
        win,card=self.popup("Reprogramar tarea",500,300);box=tk.Frame(card,bg="white");box.pack(fill="both",expand=True,padx=22,pady=20);tk.Label(box,text=t["text"],font=("Segoe UI Variable Text",11,"bold"),bg="white",wraplength=420,justify="left").pack(anchor="w",pady=(0,15));row=tk.Frame(box,bg="white");row.pack(fill="x");a=[]
        for label,val in [("Nueva fecha",t["date"]),("Nueva hora",t["time"])]:f=tk.Frame(row,bg="white");f.pack(side="left",fill="x",expand=True,padx=(0,10));tk.Label(f,text=label,font=("Segoe UI Variable Text",9,"bold"),bg="white").pack(anchor="w");e=ttk.Entry(f,style="Modern.TEntry");e.pack(fill="x",pady=(5,0));e.insert(0,val);a.append(e)
        def save():
            rem=",".join(map(str,t.get("reminders",[])));ok=self.validate(t["text"],a[0].get().strip(),a[1].get().strip(),rem)
            if not ok:return
            t.update(date=a[0].get().strip(),time=a[1].get().strip(),done=False,completed_at=None,archived=False,attended=False);self.clear_alert_state(t["id"]);self.save_tasks();self.refresh();win.destroy()
        bar=tk.Frame(box,bg="white");bar.pack(fill="x",pady=(24,0));RoundedButton(bar,"Reprogramar",save,bg=COLORS["blue"],fg="white",hover=COLORS["blue2"],width=130).pack(side="right");RoundedButton(bar,"Cancelar",win.destroy,width=100).pack(side="right",padx=7)
    def toggle_done(self):
        t=self.selected_task()
        if not t:return
        done=not t.get("done",False);t["done"]=done;t["attended"]=done;t["completed_at"]=datetime.now().isoformat(timespec="seconds") if done else None;t["archived"]=False
        if done:self.close_alerts(t["id"])
        self.save_tasks();self.refresh()
    def toggle_priority(self):
        t=self.selected_task()
        if t:t["priority"]=not t.get("priority",False);self.save_tasks();self.refresh()
    def delete_task(self):
        t=self.selected_task()
        if t and messagebox.askyesno(APP_NAME,f"¿Eliminar esta tarea?\n\n{t['text']}",parent=self):self.close_alerts(t["id"]);self.tasks.remove(t);self.save_tasks();self.refresh()
    def migrate_history(self):
        changed=False;now=datetime.now()
        for t in self.tasks:
            if t.get("done") and not t.get("completed_at"):
                # Las versiones antiguas no guardaban la fecha real de finalizacion: se migran directamente al Historico.
                t["completed_at"]=now.isoformat(timespec="seconds");t["archived"]=True;changed=True
        if changed:self.save_tasks()
        self.archive_old_completed()
    def archive_old_completed(self):
        changed=False;now=datetime.now()
        for t in self.tasks:
            if t.get("done") and not t.get("archived") and t.get("completed_at"):
                try:completed=datetime.fromisoformat(t["completed_at"])
                except:continue
                if now-completed>=timedelta(hours=24):t["archived"]=True;changed=True
        if changed:self.save_tasks();self.refresh()
    def history_tick(self):self.archive_old_completed();self.after(60000,self.history_tick)
    def restore_history(self):
        sel=self.history_tree.selection()
        if not sel:messagebox.showinfo(APP_NAME,"Selecciona una tarea del histórico.",parent=self);return
        t=next((x for x in self.tasks if x["id"]==sel[0]),None)
        if t:t.update(archived=False,done=False,completed_at=None,attended=False);self.save_tasks();self.refresh();self.select_tab("pending");self.reschedule_by_task(t)
    def reschedule_by_task(self,t):
        self.tree.selection_set(t["id"]);self.reschedule_task()
    def delete_history(self):
        sel=self.history_tree.selection()
        if not sel:return
        t=next((x for x in self.tasks if x["id"]==sel[0]),None)
        if t and messagebox.askyesno(APP_NAME,"¿Eliminar definitivamente esta tarea del histórico?",parent=self):self.tasks.remove(t);self.save_tasks();self.refresh()
    def refresh(self):
        for tr in (self.tree,self.history_tree):
            for i in tr.get_children():tr.delete(i)
        now=datetime.now()
        pending=sorted([t for t in self.tasks if not t.get("archived")],key=lambda t:(t.get("done",False),not t.get("priority",False),self.parse_dt(t)))
        for t in pending:
            if t.get("done"):status,tag="Realizada","done"
            elif self.parse_dt(t)<now:status,tag="Vencida","overdue"
            else:status,tag="Pendiente","priority" if t.get("priority") else ""
            rr=t.get("reminders",[15]);rt=", ".join(f"{x} min" for x in rr) if rr else "Solo en hora"
            self.tree.insert("","end",iid=t["id"],values=("★ ALTA" if t.get("priority") else "Normal",t["text"],t["date"],t["time"],rt,status),tags=(tag,) if tag else ())
        hist=sorted([t for t in self.tasks if t.get("archived")],key=lambda t:t.get("completed_at") or "",reverse=True)
        for t in hist:
            try:when=datetime.fromisoformat(t["completed_at"]).strftime("%d/%m/%Y %H:%M")
            except:when=""
            self.history_tree.insert("","end",iid=t["id"],values=(t["text"],when,t["date"],t["time"]),tags=("history",))
        self.pending_tab_btn.configure(text=f"Pendientes ({len(pending)})");self.history_tab_btn.configure(text=f"Histórico ({len(hist)})")
    def select_row_at_pointer(self,tree,event):
        row=tree.identify_row(event.y)
        if not row:return None
        tree.selection_set(row);tree.focus(row);return row
    def show_pending_context(self,event):
        if not self.select_row_at_pointer(self.tree,event):return
        menu=tk.Menu(self,tearoff=0,font=("Segoe UI Variable Text",10))
        menu.add_command(label="Editar",command=self.edit_task);menu.add_command(label="Reprogramar",command=self.reschedule_task);menu.add_separator()
        menu.add_command(label="Realizada / Pendiente",command=self.toggle_done);menu.add_command(label="Prioritaria / Normal",command=self.toggle_priority);menu.add_command(label="Enviar a Histórico",command=self.send_to_history);menu.add_separator();menu.add_command(label="Eliminar",command=self.delete_task)
        try:menu.tk_popup(event.x_root,event.y_root)
        finally:menu.grab_release()
    def show_history_context(self,event):
        if not self.select_row_at_pointer(self.history_tree,event):return
        menu=tk.Menu(self,tearoff=0,font=("Segoe UI Variable Text",10));menu.add_command(label="Restaurar / Reprogramar",command=self.restore_history);menu.add_separator();menu.add_command(label="Eliminar del histórico",command=self.delete_history)
        try:menu.tk_popup(event.x_root,event.y_root)
        finally:menu.grab_release()
    def send_to_history(self):
        t=self.selected_pending()
        if not t:return
        t["done"]=True;t["attended"]=True;t["completed_at"]=datetime.now().isoformat(timespec="seconds");t["archived"]=True
        self.close_alerts(t["id"]);self.save_tasks();self.refresh();self.select_tab("history")
    def clear_alert_state(self,tid):self.triggered={k for k in self.triggered if not k.startswith(tid+"_")};self.retry_counts={k:v for k,v in self.retry_counts.items() if not k.startswith(tid+"_")};self.close_alerts(tid)
    def check_reminders(self):
        """Agrupa en una sola ventana las tareas que disparan el mismo aviso."""
        now=datetime.now();groups={};needs_refresh=False
        for t in self.tasks:
            if t.get("done") or t.get("archived"):continue
            due=self.parse_dt(t);seconds=(due-now).total_seconds();tid=t["id"]
            due_stamp=due.strftime("%Y%m%d%H%M")
            for m in t.get("reminders",[15]):
                task_key=f"{tid}_pre_{m}"
                if m*60-30<seconds<=m*60 and task_key not in self.triggered:
                    self.triggered.add(task_key)
                    group_key=f"group_{due_stamp}_pre_{m}"
                    group=groups.setdefault(group_key,{"tasks":[],"heading":f"Recordatorio · faltan {m} minutos","expires":True,"task_keys":[]})
                    group["tasks"].append(t);group["task_keys"].append(task_key)
            task_key=f"{tid}_due"
            if -59<seconds<=0 and task_key not in self.triggered:
                self.triggered.add(task_key);self.close_alerts(tid)
                group_key=f"group_{due_stamp}_due"
                group=groups.setdefault(group_key,{"tasks":[],"heading":"Es la hora","expires":False,"task_keys":[]})
                group["tasks"].append(t);group["task_keys"].append(task_key);needs_refresh=True
        for group_key,data in groups.items():
            self.retry_counts.setdefault(group_key,0)
            self.show_group_alert(data["tasks"],group_key,data["heading"],data["expires"],data["task_keys"])
        if needs_refresh:self.refresh()
        self.after(1000,self.check_reminders)

    def close_alerts(self,tid):
        for key,win in list(self.active_alerts.items()):
            task_ids=getattr(win,"grouped_task_ids",set())
            if key.startswith(tid+"_") or tid in task_ids:
                try:win.destroy()
                except:pass
                self.active_alerts.pop(key,None)

    def show_group_alert(self,tasks,key,heading,expires,task_keys=None):
        if key in self.active_alerts or not tasks:return
        live=[t for t in tasks if not t.get("done") and not t.get("archived")]
        if not live:return
        try:winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except:pass
        a=tk.Toplevel(self);self.active_alerts[key]=a;a.grouped_task_ids={t["id"] for t in live}
        a.title("Recordatorio");a.attributes("-topmost",True);a.resizable(False,False);a.configure(bg=COLORS["bg"])
        card=tk.Frame(a,bg="white");card.pack(fill="both",expand=True,padx=10,pady=10)
        priority=any(t.get("priority") for t in live)
        title=("★ HAY TAREAS PRIORITARIAS\n" if priority else "")+heading
        tk.Label(card,text=title,font=("Segoe UI Variable Display",15,"bold"),fg=COLORS["red"] if priority or not expires else COLORS["blue"],bg="white").pack(pady=(22,12))
        if len(live)==1:
            body=live[0]["text"]
        else:
            body="\n".join(f"{i}. {t['text']}" for i,t in enumerate(live,1))
        tk.Label(card,text=body,font=("Segoe UI Variable Text",12,"bold"),bg="white",wraplength=560,justify="left").pack(padx=25,pady=(0,8),anchor="w")
        hour=live[0]["time"]
        tk.Label(card,text=f"{len(live)} tarea{'s' if len(live)!=1 else ''} programada{'s' if len(live)!=1 else ''} para las {hour}",font=("Segoe UI Variable Text",10),fg=COLORS["muted"],bg="white").pack()
        def accept():
            for t in live:t["attended"]=True
            self.save_tasks();self.active_alerts.pop(key,None)
            try:a.destroy()
            except:pass
            self.refresh()
        bw=tk.Frame(card,bg="white");bw.pack(pady=18);RoundedButton(bw,"Aceptar todas" if len(live)>1 else "Aceptar",accept,bg=COLORS["blue"],fg="white",hover=COLORS["blue2"],width=135 if len(live)>1 else 110).pack()
        if expires:
            attempt=self.retry_counts.get(key,0)+1
            tk.Label(card,text=f"Intento {attempt} de 3 · se repetirá si no se atiende",font=("Segoe UI Variable Text",9),fg=COLORS["muted"],bg="white").pack(pady=(0,15))
            a.after(60000,lambda:self.expire_group_alert(live,key,heading,task_keys or []))
        else:
            tk.Label(card,text="Este aviso permanecerá hasta pulsar Aceptar",font=("Segoe UI Variable Text",9),fg=COLORS["muted"],bg="white").pack(pady=(0,15))
        a.protocol("WM_DELETE_WINDOW",accept);a.update_idletasks();w=max(600,a.winfo_reqwidth());h=max(320,a.winfo_reqheight());a.geometry(f"{w}x{h}+{self.winfo_screenwidth()-w-35}+{self.winfo_screenheight()-h-80}")

    def expire_group_alert(self,tasks,key,heading,task_keys):
        win=self.active_alerts.pop(key,None)
        if win:
            try:win.destroy()
            except:pass
        count=self.retry_counts.get(key,0)+1;self.retry_counts[key]=count
        live=[t for t in tasks if not t.get("done") and not t.get("archived") and not t.get("attended")]
        if count<3 and live:self.after(500,lambda:self.show_group_alert(live,key,heading,True,task_keys))

    def load_config(self):
        defaults={"mode":"LOCAL","shared_path":"","last_technician":"","technicians":[]}
        try:
            CONFIG_DIR.mkdir(parents=True,exist_ok=True)
            if CONFIG_FILE.exists():defaults.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except Exception:pass
        return defaults
    def save_config(self):
        try:
            CONFIG_DIR.mkdir(parents=True,exist_ok=True)
            tmp=CONFIG_FILE.with_suffix(".tmp");tmp.write_text(json.dumps(self.config_data,ensure_ascii=False,indent=2),encoding="utf-8");os.replace(tmp,CONFIG_FILE)
        except Exception as e:messagebox.showerror(APP_NAME,f"No se pudo guardar la configuración:\n\n{e}",parent=self)
    def resolve_data_file(self):
        if self.config_data.get("mode")=="COMPARTIDO" and self.config_data.get("shared_path"):
            return Path(self.config_data["shared_path"])
        return LOCAL_DATA_FILE
    def data_signature(self):
        try:
            st=self.data_file.stat();return (st.st_mtime_ns,st.st_size)
        except OSError:return None
    def save_current_technician(self,event=None):
        name=self.tech_var.get().strip()
        if not name:return
        techs=self.config_data.setdefault("technicians",[])
        if name not in techs:techs.append(name);techs.sort(key=str.casefold);self.tech_combo.configure(values=techs)
        self.config_data["last_technician"]=name;self.save_config()
    def show_options(self):
        win=tk.Toplevel(self);win.title("Opciones");win.transient(self);win.grab_set();win.resizable(False,False)
        try:win.iconbitmap(str(ICON_ICO))
        except Exception:pass
        box=tk.Frame(win,bg="white",padx=24,pady=22);box.pack(fill="both",expand=True)
        tk.Label(box,text="Almacenamiento de tareas",font=("Segoe UI Variable Display",15,"bold"),bg="white",fg=COLORS["text"]).grid(row=0,column=0,columnspan=3,sticky="w",pady=(0,12))
        mode=tk.StringVar(value=self.config_data.get("mode","LOCAL"));path=tk.StringVar(value=self.config_data.get("shared_path",""))
        tk.Radiobutton(box,text="LOCAL · solo este equipo",variable=mode,value="LOCAL",bg="white",font=("Segoe UI Variable Text",10)).grid(row=1,column=0,columnspan=3,sticky="w",pady=4)
        tk.Radiobutton(box,text="COMPARTIDO · varios equipos",variable=mode,value="COMPARTIDO",bg="white",font=("Segoe UI Variable Text",10)).grid(row=2,column=0,columnspan=3,sticky="w",pady=4)
        tk.Label(box,text="Ruta del JSON compartido",font=("Segoe UI Variable Text",9,"bold"),bg="white").grid(row=3,column=0,columnspan=3,sticky="w",pady=(14,4))
        ent=ttk.Entry(box,textvariable=path,width=57);ent.grid(row=4,column=0,columnspan=2,sticky="ew",padx=(0,8))
        def browse():
            f=filedialog.asksaveasfilename(parent=win,title="Seleccionar JSON compartido",defaultextension=".json",filetypes=[("JSON de tareas","*.json"),("Todos","*.*")],initialfile="avisador_tareas.json")
            if f:path.set(f)
        ttk.Button(box,text="Examinar",command=browse).grid(row=4,column=2)
        tk.Label(box,text="Técnicos recordados",font=("Segoe UI Variable Text",9,"bold"),bg="white").grid(row=5,column=0,columnspan=3,sticky="w",pady=(18,4))
        tech=tk.StringVar(value=", ".join(self.config_data.get("technicians",[])));ttk.Entry(box,textvariable=tech,width=68).grid(row=6,column=0,columnspan=3,sticky="ew")
        tk.Label(box,text="Separar nombres por comas. El último técnico queda preseleccionado al abrir.",font=("Segoe UI Variable Text",9),bg="white",fg=COLORS["muted"]).grid(row=7,column=0,columnspan=3,sticky="w",pady=(5,16))
        def apply():
            if mode.get()=="COMPARTIDO" and not path.get().strip():messagebox.showwarning(APP_NAME,"Indica la ruta del JSON compartido.",parent=win);return
            newfile=Path(path.get().strip()) if mode.get()=="COMPARTIDO" else LOCAL_DATA_FILE
            try:
                newfile.parent.mkdir(parents=True,exist_ok=True)
                if not newfile.exists():newfile.write_text("[]",encoding="utf-8")
                json.loads(newfile.read_text(encoding="utf-8"))
            except Exception as e:messagebox.showerror(APP_NAME,f"No se puede usar esa ubicación:\n\n{e}",parent=win);return
            names=sorted({x.strip() for x in tech.get().split(",") if x.strip()},key=str.casefold)
            current=self.tech_var.get().strip()
            if current and current not in names:names.append(current)
            self.config_data.update(mode=mode.get(),shared_path=path.get().strip(),technicians=names,last_technician=current)
            self.save_config();self.data_file=self.resolve_data_file();self.tech_combo.configure(values=names);self.load_tasks();self.refresh();win.destroy()
        bar=tk.Frame(box,bg="white");bar.grid(row=8,column=0,columnspan=3,sticky="e")
        ttk.Button(bar,text="Cancelar",command=win.destroy).pack(side="right");ttk.Button(bar,text="Guardar",command=apply).pack(side="right",padx=(0,8))
        win.update_idletasks();w,h=650,390;x=self.winfo_rootx()+(self.winfo_width()-w)//2;y=self.winfo_rooty()+(self.winfo_height()-h)//2;win.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")
    def normalize_tasks(self):
        for i,t in enumerate(self.tasks):
            t.setdefault("id",f"{datetime.now().timestamp()}_{i}");t.setdefault("done",False);t.setdefault("priority",False);t.setdefault("reminders",[15]);t.setdefault("attended",False);t.setdefault("completed_at",None);t.setdefault("archived",False);t.setdefault("technician","")
    def load_tasks(self,silent=False):
        try:
            if self.data_file.exists():self.tasks=json.loads(self.data_file.read_text(encoding="utf-8"))
            else:self.tasks=[]
            self.normalize_tasks();self.last_data_signature=self.data_signature()
        except Exception as e:
            if not silent:messagebox.showerror(APP_NAME,f"No se pudieron cargar las tareas desde:\n{self.data_file}\n\n{e}",parent=self)
    def acquire_lock(self,timeout=5):
        lock=Path(str(self.data_file)+".lock");limit=time.time()+timeout
        while time.time()<limit:
            try:
                fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,f"{os.getpid()} {time.time()}".encode());return lock,fd
            except FileExistsError:
                try:
                    if time.time()-lock.stat().st_mtime>30:lock.unlink(missing_ok=True);continue
                except OSError:pass
                time.sleep(.1)
        raise TimeoutError("El archivo está siendo actualizado por otro equipo.")
    def save_tasks(self):
        lock=fd=None
        try:
            self.data_file.parent.mkdir(parents=True,exist_ok=True);lock,fd=self.acquire_lock()
            payload=json.dumps(self.tasks,ensure_ascii=False,indent=2)
            tmp=Path(str(self.data_file)+f".{os.getpid()}.tmp");tmp.write_text(payload,encoding="utf-8");os.replace(tmp,self.data_file)
            self.last_data_signature=self.data_signature()
        except Exception as e:messagebox.showerror(APP_NAME,f"No se pudieron guardar las tareas en:\n{self.data_file}\n\n{e}",parent=self)
        finally:
            if fd is not None:os.close(fd)
            if lock is not None:
                try:lock.unlink(missing_ok=True)
                except OSError:pass
    def auto_reload_tasks(self):
        try:
            sig=self.data_signature()
            if sig is not None and self.last_data_signature is not None and sig!=self.last_data_signature:
                self.load_tasks(silent=True);self.migrate_history();self.refresh()
        finally:self.after(3000,self.auto_reload_tasks)
    def start_tray(self):
        if pystray is None or Image is None or self.tray_icon is not None:return
        img=Image.open(ICON_PNG).convert("RGBA");img.thumbnail((256,256),Image.Resampling.LANCZOS);menu=pystray.Menu(pystray.MenuItem("Abrir Avisador",self.tray_show,default=True),pystray.MenuItem("Salir",self.tray_exit));self.tray_icon=pystray.Icon("avisador_tareas",img,APP_NAME,menu);self.tray_thread=threading.Thread(target=self.tray_icon.run,daemon=True);self.tray_thread.start()
    def on_minimize(self,e=None):
        if self.state()=="iconic":self.after(10,self.hide_to_tray)
    def hide_to_tray(self):
        if pystray is None or Image is None:messagebox.showerror(APP_NAME,"Faltan pystray o Pillow.",parent=self);return
        self.withdraw();self.start_tray()
    def tray_show(self,i=None,item=None):self.after(0,self.restore_window)
    def restore_window(self):self.deiconify();self.state("normal");self.lift();self.focus_force()
    def tray_exit(self,i=None,item=None):
        if self.tray_icon:self.tray_icon.stop();self.tray_icon=None
        self.after(0,self.destroy)
if __name__=="__main__":App().mainloop()

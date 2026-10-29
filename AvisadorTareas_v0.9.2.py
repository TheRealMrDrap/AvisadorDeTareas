import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import json, sys, threading
from pathlib import Path
import winsound

try:
    import pystray
    from PIL import Image
except ImportError:
    pystray = None
    Image = None

APP_NAME = "Avisador de Tareas v0.9.2"
DATA_FILE = Path.home() / "avisador_tareas.json"
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
        self.set_icon();self.protocol("WM_DELETE_WINDOW",self.hide_to_tray);self.bind("<Unmap>",self.on_minimize)
        self.styles();self.build_ui();self.load_tasks();self.migrate_history();self.refresh();self.after(1000,self.check_reminders);self.after(60000,self.history_tick)
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
        tk.Label(main,text="Avisador de tareas",font=("Segoe UI Variable Display",22,"bold"),bg=COLORS["bg"],fg=COLORS["text"]).pack(anchor="w")
        tk.Label(main,text="Recordatorios locales, rápidos y sin depender de Outlook",font=("Segoe UI Variable Text",10),bg=COLORS["bg"],fg=COLORS["muted"]).pack(anchor="w",pady=(2,14))
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
        self.tasks.append({"id":str(datetime.now().timestamp()),"text":v[0],"date":v[1],"time":v[2],"reminders":ok[1],"done":False,"priority":False,"attended":False,"completed_at":None,"archived":False});self.save_tasks();self.refresh();self.txt_task.delete(0,"end")
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
        now=datetime.now()
        for t in self.tasks:
            if t.get("done") or t.get("archived"):continue
            seconds=(self.parse_dt(t)-now).total_seconds();tid=t["id"]
            for m in t.get("reminders",[15]):
                key=f"{tid}_pre_{m}"
                if m*60-30<seconds<=m*60 and key not in self.triggered:self.triggered.add(key);self.retry_counts[key]=0;self.show_alert(t,key,f"Recordatorio · faltan {m} minutos",True)
            key=f"{tid}_due"
            if -59<seconds<=0 and key not in self.triggered:self.triggered.add(key);self.close_alerts(tid);self.show_alert(t,key,"Es la hora",False);self.refresh()
        self.after(1000,self.check_reminders)
    def close_alerts(self,tid):
        for k,w in list(self.active_alerts.items()):
            if k.startswith(tid+"_"):
                try:w.destroy()
                except:pass
                self.active_alerts.pop(k,None)
    def show_alert(self,t,key,heading,expires):
        if key in self.active_alerts:return
        try:winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except:pass
        a=tk.Toplevel(self);self.active_alerts[key]=a;a.title("Recordatorio");a.attributes("-topmost",True);a.resizable(False,False);a.configure(bg=COLORS["bg"])
        card=tk.Frame(a,bg="white");card.pack(fill="both",expand=True,padx=10,pady=10)
        tk.Label(card,text=("★ PRIORITARIA\n" if t.get("priority") else "")+heading,font=("Segoe UI Variable Display",15,"bold"),fg=COLORS["red"] if t.get("priority") or not expires else COLORS["blue"],bg="white").pack(pady=(22,12));tk.Label(card,text=t["text"],font=("Segoe UI Variable Text",12,"bold"),bg="white",wraplength=480).pack(padx=22,pady=(0,8));tk.Label(card,text=f"Programada para las {t['time']}",font=("Segoe UI Variable Text",10),fg=COLORS["muted"],bg="white").pack()
        def accept():t["attended"]=True;self.save_tasks();self.active_alerts.pop(key,None);a.destroy();self.refresh()
        bw=tk.Frame(card,bg="white");bw.pack(pady=18);RoundedButton(bw,"Aceptar",accept,bg=COLORS["blue"],fg="white",hover=COLORS["blue2"],width=110).pack()
        if expires:
            attempt=self.retry_counts.get(key,0)+1;tk.Label(card,text=f"Intento {attempt} de 3 · se repetirá si no se atiende",font=("Segoe UI Variable Text",9),fg=COLORS["muted"],bg="white").pack(pady=(0,15));a.after(60000,lambda:self.expire_alert(t,key,heading))
        else:tk.Label(card,text="Este aviso permanecerá hasta pulsar Aceptar",font=("Segoe UI Variable Text",9),fg=COLORS["muted"],bg="white").pack(pady=(0,15))
        a.protocol("WM_DELETE_WINDOW",accept);a.update_idletasks();w=max(550,a.winfo_reqwidth());h=max(300,a.winfo_reqheight());a.geometry(f"{w}x{h}+{self.winfo_screenwidth()-w-35}+{self.winfo_screenheight()-h-80}")
    def expire_alert(self,t,key,heading):
        w=self.active_alerts.pop(key,None)
        if w:
            try:w.destroy()
            except:pass
        n=self.retry_counts.get(key,0)+1;self.retry_counts[key]=n
        if n<3 and not t.get("done"):self.after(500,lambda:self.show_alert(t,key,heading,True))
    def load_tasks(self):
        try:
            if DATA_FILE.exists():self.tasks=json.loads(DATA_FILE.read_text(encoding="utf-8"))
            for i,t in enumerate(self.tasks):t.setdefault("id",f"{datetime.now().timestamp()}_{i}");t.setdefault("done",False);t.setdefault("priority",False);t.setdefault("reminders",[15]);t.setdefault("attended",False);t.setdefault("completed_at",None);t.setdefault("archived",False)
        except Exception as e:self.tasks=[];messagebox.showerror(APP_NAME,f"No se pudieron cargar las tareas:\n\n{e}",parent=self)
    def save_tasks(self):
        try:DATA_FILE.write_text(json.dumps(self.tasks,ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception as e:messagebox.showerror(APP_NAME,f"No se pudieron guardar las tareas:\n\n{e}",parent=self)
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

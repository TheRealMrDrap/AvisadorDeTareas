import json, os, sys, threading, tempfile
from pathlib import Path
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import winsound
try:
    import pystray
    from PIL import Image, ImageDraw, ImageTk
except ImportError:
    pystray=Image=ImageDraw=ImageTk=None

APP_NAME='Avisador de Tareas v0.9.7'
LOCAL_DIR=Path(os.getenv('LOCALAPPDATA',Path.home()))/'AvisadorTareas'
LOCAL_DIR.mkdir(parents=True,exist_ok=True)
CONFIG_FILE=LOCAL_DIR/'config.json'
DEFAULT_DATA=Path.home()/'avisador_tareas.json'
COL={'bg':'#F3F5F8','card':'#FFFFFF','text':'#202124','muted':'#6B7280','blue':'#1677FF','blue2':'#0F66DD','red':'#C62828','green':'#18864B','line':'#E3E6EA','select':'#DCEBFF'}

def resource(name):
    return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/name
ICON_PNG=resource('AvisadorTareas_Icono_512.png'); ICON_ICO=resource('Mantenimiento.ico')

class PillButton(tk.Canvas):
    def __init__(self,parent,text,command,width=120,bg='#EEF1F5',fg='#202124',hover='#E1E6EC'):
        super().__init__(parent,width=width,height=38,bg=parent.cget('bg'),highlightthickness=0,bd=0,cursor='hand2')
        self.text,self.command,self.w,self.normal,self.hover,self.fg=text,command,width,bg,hover,fg;self.photo=None
        self.bind('<Enter>',lambda e:self.draw(hover));self.bind('<Leave>',lambda e:self.draw(bg));self.bind('<Button-1>',lambda e:self.draw(hover));self.bind('<ButtonRelease-1>',self.run);self.draw(bg)
    def draw(self,color):
        self.delete('all')
        if Image:
            sc=4;im=Image.new('RGBA',(self.w*sc,38*sc),(0,0,0,0));d=ImageDraw.Draw(im)
            d.rounded_rectangle((4*sc,5*sc,(self.w-2)*sc,37*sc),radius=17*sc,fill='#D9DEE5')
            d.rounded_rectangle((1*sc,1*sc,(self.w-3)*sc,34*sc),radius=17*sc,fill=color)
            im=im.resize((self.w,38),Image.Resampling.LANCZOS);self.photo=ImageTk.PhotoImage(im);self.create_image(0,0,image=self.photo,anchor='nw')
        else:self.create_rectangle(1,1,self.w-3,34,fill=color,outline='')
        self.create_text(self.w/2-1,17,text=self.text,fill=self.fg,font=('Segoe UI Variable Text',10,'bold'))
    def run(self,e):
        self.draw(self.hover)
        if self.command:self.command()

class App(tk.Tk):
    def __init__(self):
        super().__init__();self.title(APP_NAME);self.geometry('1280x720');self.minsize(1080,600);self.configure(bg=COL['bg'])
        self.config_data=self.load_config();self.data_file=Path(self.config_data.get('ruta_tareas',str(DEFAULT_DATA)))
        self.tasks=[];self.triggered=set();self.alerts={};self.retry={};self.tray=None
        try:self.iconbitmap(str(ICON_ICO))
        except:pass
        self.protocol('WM_DELETE_WINDOW',self.hide);self.bind('<Unmap>',self.minimized)
        self.style();self.ui();self.load_tasks();self.migrate();self.refresh();self.after(1000,self.check);self.after(60000,self.archive_tick)
    def load_config(self):
        base={'tecnico_actual':'Sin asignar','tecnicos':['Sin asignar'],'ruta_tareas':str(DEFAULT_DATA)}
        try:
            if CONFIG_FILE.exists():base.update(json.loads(CONFIG_FILE.read_text(encoding='utf-8')))
        except:pass
        base['tecnicos']=list(dict.fromkeys(['Sin asignar']+base.get('tecnicos',[])+[base.get('tecnico_actual','Sin asignar')]))
        return base
    def save_config(self):CONFIG_FILE.write_text(json.dumps(self.config_data,ensure_ascii=False,indent=2),encoding='utf-8')
    def style(self):
        s=ttk.Style(self)
        try:s.theme_use('clam')
        except:pass
        s.configure('.',font=('Segoe UI Variable Text',10),background=COL['bg'],foreground=COL['text']);s.configure('Modern.TEntry',padding=9,fieldbackground='#FAFBFC',bordercolor=COL['line'])
        s.configure('Treeview',font=('Segoe UI Variable Text',10),rowheight=38,background='white',fieldbackground='white',borderwidth=0);s.configure('Treeview.Heading',font=('Segoe UI Variable Text',9,'bold'),background='#F6F7F9',foreground=COL['muted'],padding=(8,10));s.map('Treeview',background=[('selected',COL['select'])],foreground=[('selected',COL['text'])])
    def ui(self):
        main=tk.Frame(self,bg=COL['bg']);main.pack(fill='both',expand=True,padx=22,pady=18)
        head=tk.Frame(main,bg=COL['bg']);head.pack(fill='x');tk.Label(head,text='Avisador de tareas',font=('Segoe UI Variable Display',22,'bold'),bg=COL['bg']).pack(side='left')
        self.tech_label=tk.Label(head,text=f"Técnico: {self.config_data['tecnico_actual']}",font=('Segoe UI Variable Text',10,'bold'),bg=COL['bg'],fg=COL['blue']);self.tech_label.pack(side='right',padx=(10,0));PillButton(head,'Opciones',self.options,100).pack(side='right')
        tk.Label(main,text='Recordatorios locales con técnico asignado',font=('Segoe UI Variable Text',10),bg=COL['bg'],fg=COL['muted']).pack(anchor='w',pady=(2,14))
        card=tk.Frame(main,bg='white',highlightthickness=1,highlightbackground=COL['line']);card.pack(fill='x',pady=(0,12));f=tk.Frame(card,bg='white');f.pack(fill='x',padx=17,pady=14)
        for c,t in enumerate(['Tarea','Fecha','Hora','Avisos previos','Técnico']):tk.Label(f,text=t,font=('Segoe UI Variable Text',9,'bold'),bg='white').grid(row=0,column=c,sticky='w')
        self.e_task=ttk.Entry(f,style='Modern.TEntry');self.e_date=ttk.Entry(f,width=14,style='Modern.TEntry');self.e_time=ttk.Entry(f,width=9,style='Modern.TEntry');self.e_rem=ttk.Entry(f,width=18,style='Modern.TEntry');self.tech_var=tk.StringVar(value=self.config_data['tecnico_actual']);self.tech_combo=ttk.Combobox(f,textvariable=self.tech_var,values=self.config_data['tecnicos'],state='readonly',width=17)
        for c,e in enumerate([self.e_task,self.e_date,self.e_time,self.e_rem,self.tech_combo]):e.grid(row=1,column=c,sticky='ew',padx=(0,9),pady=(5,0))
        b=tk.Frame(f,bg='white');b.grid(row=1,column=5);PillButton(b,'Añadir tarea',self.add,132,COL['blue'],'white',COL['blue2']).pack();f.columnconfigure(0,weight=1)
        n=datetime.now();self.e_date.insert(0,n.strftime('%d/%m/%Y'));self.e_time.insert(0,(n+timedelta(hours=1)).strftime('%H:%M'));self.e_rem.insert(0,'15')
        actions=tk.Frame(main,bg='white',highlightthickness=1,highlightbackground=COL['line']);actions.pack(fill='x',pady=(0,12));a=tk.Frame(actions,bg='white');a.pack(fill='x',padx=13,pady=9)
        for text,cmd,w in [('Editar',self.edit,90),('Reprogramar',self.reschedule,120),('Reasignar',self.reassign,110),('Realizada / Pendiente',self.done,170),('Prioritaria / Normal',self.priority,160)]:PillButton(a,text,cmd,w).pack(side='left',padx=(0,7))
        PillButton(a,'Eliminar',self.delete,90,'#FCE8E8',COL['red'],'#F7D4D4').pack(side='left');PillButton(a,'Ocultar',self.hide,90).pack(side='right')
        self.tabbar=tk.Frame(main,bg=COL['bg'],height=45);self.tabbar.pack(fill='x');self.tabbar.pack_propagate(False)
        self.bp=tk.Label(self.tabbar,text='Pendientes (0)',width=18,height=2,font=('Segoe UI Variable Text',10,'bold'),cursor='hand2');self.bh=tk.Label(self.tabbar,text='Histórico (0)',width=18,height=2,font=('Segoe UI Variable Text',10,'bold'),cursor='hand2');self.bp.pack(side='left',padx=(0,4));self.bh.pack(side='left');self.bp.bind('<Button-1>',lambda e:self.tab('p'));self.bh.bind('<Button-1>',lambda e:self.tab('h'))
        area=tk.Frame(main,bg='white',highlightthickness=1,highlightbackground=COL['line']);area.pack(fill='both',expand=True);self.fp=tk.Frame(area,bg='white');self.fh=tk.Frame(area,bg='white');self.fp.place(x=0,y=0,relwidth=1,relheight=1);self.fh.place(x=0,y=0,relwidth=1,relheight=1)
        self.tree=self.make_tree(self.fp,False);self.hist=self.make_tree(self.fh,True);self.tree.bind('<Button-3>',self.context_pending);self.hist.bind('<Button-3>',self.context_history);self.tree.bind('<Double-1>',lambda e:self.edit());self.hist.bind('<Double-1>',lambda e:self.restore());self.tab('p')
    def tab(self,w):
        (self.fh if w=='h' else self.fp).tkraise()
        self.bp.config(bg='white' if w=='p' else '#E3E8EF',fg=COL['blue'] if w=='p' else COL['text']);self.bh.config(bg='white' if w=='h' else '#E3E8EF',fg=COL['blue'] if w=='h' else COL['text'])
    def make_tree(self,parent,hist):
        wrap=tk.Frame(parent,bg='white');wrap.pack(fill='both',expand=True);cols=('task','tech','completed','date','time') if hist else ('priority','task','tech','date','time','reminders','status');tr=ttk.Treeview(wrap,columns=cols,show='headings',selectmode='browse')
        names={'priority':'PRIORIDAD','task':'TAREA','tech':'TÉCNICO','completed':'REALIZADA EL','date':'FECHA','time':'HORA','reminders':'AVISOS','status':'ESTADO'}
        for c in cols:tr.heading(c,text=names[c]);tr.column(c,width=120,anchor='center')
        tr.column('task',width=390,anchor='w');tr.tag_configure('red',foreground=COL['red'],font=('Segoe UI Variable Text',10,'bold'));tr.tag_configure('green',foreground=COL['green'],font=('Segoe UI Variable Text',10,'bold'))
        tr.pack(side='left',fill='both',expand=True);sb=ttk.Scrollbar(wrap,command=tr.yview);sb.pack(side='right',fill='y');tr.config(yscrollcommand=sb.set);return tr
    def parse_dt(self,t):return datetime.strptime(t['date']+' '+t['time'],'%d/%m/%Y %H:%M')
    def selected(self):
        s=self.tree.selection()
        if not s:messagebox.showinfo(APP_NAME,'Selecciona una tarea.',parent=self);return None
        return next((x for x in self.tasks if x['id']==s[0]),None)
    def parse_rem(self,x):
        if not x.strip():return []
        try:r=sorted({int(v.strip()) for v in x.split(',') if v.strip()},reverse=True)
        except:raise ValueError('Avisos: minutos separados por comas.')
        if any(v<1 or v>10080 for v in r):raise ValueError('Los avisos deben estar entre 1 y 10080 minutos.')
        return r
    def add(self):
        try:dt=datetime.strptime(self.e_date.get()+' '+self.e_time.get(),'%d/%m/%Y %H:%M');rr=self.parse_rem(self.e_rem.get())
        except ValueError as e:messagebox.showerror(APP_NAME,str(e),parent=self);return
        if not self.e_task.get().strip() or dt<=datetime.now():messagebox.showwarning(APP_NAME,'Escribe una tarea con fecha futura.',parent=self);return
        self.tasks.append({'id':str(datetime.now().timestamp()),'text':self.e_task.get().strip(),'date':self.e_date.get(),'time':self.e_time.get(),'reminders':rr,'technician':self.tech_var.get(),'done':False,'priority':False,'attended':False,'completed_at':None,'archived':False});self.save_tasks();self.refresh();self.e_task.delete(0,'end')
    def popup(self,title,w,h):
        x=tk.Toplevel(self);x.title(title);x.transient(self);x.grab_set();x.resizable(False,False);x.configure(bg=COL['bg']);self.update_idletasks();px=self.winfo_rootx()+(self.winfo_width()-w)//2;py=self.winfo_rooty()+(self.winfo_height()-h)//2;x.geometry(f'{w}x{h}+{px}+{py}');c=tk.Frame(x,bg='white');c.pack(fill='both',expand=True,padx=12,pady=12);return x,c
    def edit(self):
        t=self.selected()
        if not t:return
        w,c=self.popup('Editar tarea',560,470);entries=[]
        for lab,val in [('Tarea',t['text']),('Fecha',t['date']),('Hora',t['time']),('Avisos',','.join(map(str,t['reminders']))),('Técnico',t['technician'])]:tk.Label(c,text=lab,bg='white',font=('Segoe UI Variable Text',9,'bold')).pack(anchor='w',padx=20);e=ttk.Entry(c);e.pack(fill='x',padx=20,pady=(3,8));e.insert(0,val);entries.append(e)
        def save():
            try:datetime.strptime(entries[1].get()+' '+entries[2].get(),'%d/%m/%Y %H:%M');rr=self.parse_rem(entries[3].get())
            except ValueError as e:messagebox.showerror(APP_NAME,str(e),parent=w);return
            t.update(text=entries[0].get().strip(),date=entries[1].get(),time=entries[2].get(),reminders=rr,technician=entries[4].get().strip() or 'Sin asignar');self.ensure_tech(t['technician']);self.save_tasks();self.refresh();w.destroy()
        PillButton(c,'Guardar',save,110,COL['blue'],'white',COL['blue2']).pack(pady=8)
    def reschedule(self):
        t=self.selected()
        if not t:return
        w,c=self.popup('Reprogramar',460,250);es=[]
        for lab,val in [('Nueva fecha',t['date']),('Nueva hora',t['time'])]:tk.Label(c,text=lab,bg='white').pack();e=ttk.Entry(c);e.pack(pady=5);e.insert(0,val);es.append(e)
        def save():
            try:dt=datetime.strptime(es[0].get()+' '+es[1].get(),'%d/%m/%Y %H:%M')
            except:messagebox.showerror(APP_NAME,'Fecha u hora incorrecta.',parent=w);return
            if dt<=datetime.now():messagebox.showwarning(APP_NAME,'Debe ser futura.',parent=w);return
            t.update(date=es[0].get(),time=es[1].get(),done=False,archived=False,completed_at=None,attended=False);self.save_tasks();self.refresh();w.destroy()
        PillButton(c,'Reprogramar',save,125,COL['blue'],'white',COL['blue2']).pack(pady=12)
    def reassign(self):
        t=self.selected()
        if not t:return
        w,c=self.popup('Reasignar técnico',460,230);tk.Label(c,text=t['text'],bg='white',font=('Segoe UI Variable Text',11,'bold'),wraplength=390).pack(pady=(18,12));v=tk.StringVar(value=t['technician']);combo=ttk.Combobox(c,textvariable=v,values=self.config_data['tecnicos'],state='readonly',width=28);combo.pack(pady=6)
        def add_technician():
            name=simpledialog.askstring('Nuevo técnico','Nombre del técnico:',parent=w)
            if name and name.strip():
                name=name.strip();self.ensure_tech(name);combo['values']=self.config_data['tecnicos'];v.set(name);self.update_techs()
        def save():
            name=v.get().strip() or 'Sin asignar';self.ensure_tech(name);t['technician']=name;self.save_tasks();self.refresh();w.destroy()
        buttons=tk.Frame(c,bg='white');buttons.pack(pady=16)
        PillButton(buttons,'Nuevo técnico',add_technician,135).pack(side='left',padx=4)
        PillButton(buttons,'Guardar asignación',save,160,COL['blue'],'white',COL['blue2']).pack(side='left',padx=4)
    def done(self):
        t=self.selected()
        if not t:return
        t['done']=not t['done'];t['completed_at']=datetime.now().isoformat(timespec='seconds') if t['done'] else None;t['archived']=False;self.save_tasks();self.refresh()
    def priority(self):
        t=self.selected()
        if t:t['priority']=not t['priority'];self.save_tasks();self.refresh()
    def delete(self):
        t=self.selected()
        if t and messagebox.askyesno(APP_NAME,'¿Eliminar la tarea?',parent=self):self.tasks.remove(t);self.save_tasks();self.refresh()
    def send_history(self):
        t=self.selected()
        if t:t.update(done=True,archived=True,completed_at=datetime.now().isoformat(timespec='seconds'));self.save_tasks();self.refresh();self.tab('h')
    def restore(self):
        s=self.hist.selection()
        if not s:return
        t=next((x for x in self.tasks if x['id']==s[0]),None)
        if t:t.update(done=False,archived=False,completed_at=None);self.save_tasks();self.refresh();self.tab('p')
    def context_pending(self,e):
        r=self.tree.identify_row(e.y)
        if not r:return
        self.tree.selection_set(r);m=tk.Menu(self,tearoff=0);[(m.add_command(label=a,command=b)) for a,b in [('Editar',self.edit),('Reprogramar',self.reschedule),('Reasignar',self.reassign),('Realizada / Pendiente',self.done),('Prioritaria / Normal',self.priority),('Enviar a Histórico',self.send_history),('Eliminar',self.delete)]];m.tk_popup(e.x_root,e.y_root)
    def context_history(self,e):
        r=self.hist.identify_row(e.y)
        if not r:return
        self.hist.selection_set(r);m=tk.Menu(self,tearoff=0);m.add_command(label='Restaurar',command=self.restore);m.tk_popup(e.x_root,e.y_root)
    def options(self):
        w,c=self.popup('Opciones',600,420);tk.Label(c,text='Opciones',bg='white',font=('Segoe UI Variable Display',18,'bold')).pack(pady=(18,12));self.opt_tech=tk.Label(c,text=f"Técnico actual: {self.config_data['tecnico_actual']}",bg='white');self.opt_tech.pack(pady=7)
        tech_choice=tk.StringVar(value=self.config_data['tecnico_actual'])
        tech_selector=ttk.Combobox(c,textvariable=tech_choice,values=self.config_data['tecnicos'],state='readonly',width=30);tech_selector.pack(pady=6)
        def apply_technician(name):
            name=(name or 'Sin asignar').strip();self.ensure_tech(name);self.config_data['tecnico_actual']=name;self.tech_var.set(name);self.tech_label.config(text=f'Técnico: {name}');self.opt_tech.config(text=f'Técnico actual: {name}');self.save_config();self.update_techs();tech_selector['values']=self.config_data['tecnicos'];tech_choice.set(name)
        def change_tech():apply_technician(tech_choice.get())
        def new_tech():
            name=simpledialog.askstring('Nuevo técnico','Nombre del técnico:',parent=w)
            if name and name.strip():apply_technician(name.strip())
        tech_buttons=tk.Frame(c,bg='white');tech_buttons.pack(pady=6)
        PillButton(tech_buttons,'Cambiar técnico',change_tech,150).pack(side='left',padx=4)
        PillButton(tech_buttons,'Nuevo técnico',new_tech,130).pack(side='left',padx=4)
        tk.Label(c,text='Archivo de tareas compartido:',bg='white').pack(pady=(18,4));path=tk.Entry(c,width=70);path.pack();path.insert(0,str(self.data_file))
        def browse():
            p=filedialog.asksaveasfilename(parent=w,title='Seleccionar JSON de tareas',defaultextension='.json',filetypes=[('JSON','*.json')])
            if p:path.delete(0,'end');path.insert(0,p)
        def apply_path():
            new=Path(path.get().strip())
            if not new.parent.exists():messagebox.showerror(APP_NAME,'La carpeta indicada no existe.',parent=w);return
            self.config_data['ruta_tareas']=str(new);self.save_config();self.data_file=new;self.load_tasks();self.refresh();w.destroy()
        bb=tk.Frame(c,bg='white');bb.pack(pady=8);PillButton(bb,'Examinar',browse,100).pack(side='left',padx=4);PillButton(bb,'Guardar opciones',apply_path,145,COL['blue'],'white',COL['blue2']).pack(side='left',padx=4)
    def ensure_tech(self,n):
        if n not in self.config_data['tecnicos']:self.config_data['tecnicos'].append(n);self.save_config()
    def update_techs(self):self.tech_combo['values']=self.config_data['tecnicos']
    def migrate(self):
        changed=False
        for t in self.tasks:
            if not t.get('technician'):t['technician']=self.config_data['tecnico_actual'];changed=True
        if changed:self.save_tasks()
    def archive_tick(self):
        now=datetime.now();changed=False
        for t in self.tasks:
            if t.get('done') and not t.get('archived') and t.get('completed_at'):
                try:
                    if now-datetime.fromisoformat(t['completed_at'])>=timedelta(hours=24):t['archived']=True;changed=True
                except:pass
        if changed:self.save_tasks();self.refresh()
        self.after(60000,self.archive_tick)
    def refresh(self):
        for tr in (self.tree,self.hist):
            for i in tr.get_children():tr.delete(i)
        now=datetime.now();p=[t for t in self.tasks if not t.get('archived')];h=[t for t in self.tasks if t.get('archived')]
        for t in sorted(p,key=lambda x:(x.get('done'),not x.get('priority'),self.parse_dt(x))):
            st='Realizada' if t.get('done') else ('Vencida' if self.parse_dt(t)<now else 'Pendiente');tag='green' if t.get('done') else ('red' if st=='Vencida' or t.get('priority') else '')
            self.tree.insert('', 'end',iid=t['id'],values=('★ ALTA' if t.get('priority') else 'Normal',t['text'],t['technician'],t['date'],t['time'],','.join(map(str,t['reminders'])) or 'Solo en hora',st),tags=(tag,) if tag else ())
        for t in h:self.hist.insert('', 'end',iid=t['id'],values=(t['text'],t['technician'],t.get('completed_at',''),t['date'],t['time']))
        self.bp.config(text=f'Pendientes ({len(p)})');self.bh.config(text=f'Histórico ({len(h)})')
    def check(self):
        now=datetime.now();groups={}
        for t in self.tasks:
            if t.get('done') or t.get('archived'):continue
            sec=(self.parse_dt(t)-now).total_seconds()
            if -59<sec<=0:groups.setdefault(('due',t['date'],t['time']),[]).append(t)
            for m in t.get('reminders',[]):
                if m*60-30<sec<=m*60:groups.setdefault((f'pre{m}',t['date'],t['time']),[]).append(t)
        for key,ts in groups.items():
            k='|'.join(key)
            if k not in self.triggered:self.triggered.add(k);self.group_alert(k,ts,key[0]=='due')
        self.after(1000,self.check)
    def group_alert(self,key,ts,due):
        a=tk.Toplevel(self);a.title('Recordatorio');a.attributes('-topmost',True);a.configure(bg='white');tk.Label(a,text='ES LA HORA' if due else 'RECORDATORIO',font=('Segoe UI Variable Display',15,'bold'),bg='white',fg=COL['red'] if due else COL['blue']).pack(pady=(20,12));text='\n'.join(f"{i+1}. {t['text']} — {t['technician']}" for i,t in enumerate(ts));tk.Label(a,text=text,font=('Segoe UI Variable Text',11,'bold'),bg='white',justify='left',wraplength=540).pack(padx=25);tk.Label(a,text=f"{len(ts)} tarea(s) programadas para las {ts[0]['time']}",bg='white',fg=COL['muted']).pack(pady=12)
        def ok():
            for t in ts:t['attended']=True
            self.save_tasks();a.destroy()
        PillButton(a,'Aceptar todas',ok,145,COL['blue'],'white',COL['blue2']).pack(pady=(0,20))
    def load_tasks(self):
        try:
            self.tasks=json.loads(self.data_file.read_text(encoding='utf-8')) if self.data_file.exists() else []
            for i,t in enumerate(self.tasks):t.setdefault('id',f'{datetime.now().timestamp()}_{i}');t.setdefault('reminders',[15]);t.setdefault('done',False);t.setdefault('priority',False);t.setdefault('attended',False);t.setdefault('completed_at',None);t.setdefault('archived',False);t.setdefault('technician',self.config_data['tecnico_actual'])
        except Exception as e:self.tasks=[];messagebox.showerror(APP_NAME,f'No se pudo cargar el JSON:\n{e}',parent=self)
    def save_tasks(self):
        try:
            self.data_file.parent.mkdir(parents=True,exist_ok=True);tmp=self.data_file.with_suffix('.tmp');tmp.write_text(json.dumps(self.tasks,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,self.data_file)
        except Exception as e:messagebox.showerror(APP_NAME,f'No se pudo guardar el JSON:\n{e}',parent=self)
    def minimized(self,e=None):
        if self.state()=='iconic':self.after(10,self.hide)
    def hide(self):
        self.withdraw()
        if pystray and not self.tray:
            img=Image.open(ICON_PNG).convert('RGBA');menu=pystray.Menu(pystray.MenuItem('Abrir',lambda i,x:self.after(0,self.show)),pystray.MenuItem('Salir',lambda i,x:self.after(0,self.destroy)));self.tray=pystray.Icon('avisador',img,APP_NAME,menu);threading.Thread(target=self.tray.run,daemon=True).start()
    def show(self):self.deiconify();self.state('normal');self.lift()
if __name__=='__main__':App().mainloop()

"""AI Laptop Manager v1.0 - offline Windows PC care desktop application.

Read-only diagnostics; the only cleanup action requires explicit confirmation.
"""
import json
import os
import queue
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import maintenance as m

BG="#101522"; PANEL="#1a2234"; FG="#ecf3ff"; MUTED="#afc0d6"
ACCENT="#66c4ff"; WARN="#ffbc69"; FONT="Segoe UI"

class LaptopManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Laptop Manager v1.0 | Local PC Health")
        self.geometry("1130x760");self.minsize(860,590);self.configure(bg=BG)
        self.messages=queue.Queue();self.temp_rows={};self.file_rows={}
        self.configure_styles()
        tk.Label(self,text="AI LAPTOP MANAGER",font=(FONT,21,"bold"),fg=ACCENT,bg=BG).pack(anchor="w",padx=20,pady=(16,0))
        tk.Label(self,text="Local diagnostics  •  No cloud uploads  •  You approve every cleanup",
                 fg=MUTED,bg=BG,font=(FONT,10)).pack(anchor="w",padx=20,pady=(0,8))
        self.tabs=ttk.Notebook(self);self.tabs.pack(fill="both",expand=True,padx=18,pady=8)
        self.views={}
        for name in ("Dashboard","Processes","Storage Explorer","Installed Apps","Startup","Safe Cleanup","Health & Reports"):
            p=tk.Frame(self.tabs,bg=BG);self.tabs.add(p,text=name);self.views[name]=p
        self.build_dashboard()
        self.build_processes()
        self.build_storage()
        self.build_apps()
        self.build_startup()
        self.build_cleanup()
        self.build_health()
        self.status=tk.Label(self,text="Ready. Diagnostic scans are read-only.",fg=MUTED,bg=BG,anchor="w")
        self.status.pack(fill="x",padx=22,pady=(2,12))
        self.after(100,self.poll)
        self.after(350,self.refresh_dashboard)

    def configure_styles(self):
        s=ttk.Style(self);s.theme_use("clam")
        s.configure("TNotebook",background=BG,borderwidth=0)
        s.configure("TNotebook.Tab",background="#253047",foreground=FG,padding=(12,10))
        s.map("TNotebook.Tab",background=[("selected",ACCENT)],foreground=[("selected",BG)])
        s.configure("Treeview",background=PANEL,fieldbackground=PANEL,foreground=FG,rowheight=28)
        s.map("Treeview",background=[("selected","#276591")],foreground=[("selected","white")])
        s.configure("Treeview.Heading",background="#253047",foreground=FG)
        s.configure("Horizontal.TProgressbar",troughcolor="#253047",background=ACCENT)

    def heading(self,tab,title,detail):
        p=self.views[tab]
        tk.Label(p,text=title,font=(FONT,17,"bold"),bg=BG,fg=FG).pack(anchor="w",padx=10,pady=(12,4))
        tk.Label(p,text=detail,bg=BG,fg=MUTED,font=(FONT,10),wraplength=950,justify="left").pack(anchor="w",padx=10,pady=(0,12))
        return p

    def button(self,parent,text,fn):
        b=tk.Button(parent,text=text,command=fn,font=(FONT,10,"bold"),bg="#293a53",fg=FG,
                    activebackground=ACCENT,relief="flat",padx=14,pady=8,cursor="hand2")
        b.pack(side="left",padx=(0,8));return b

    def toolbar(self,parent):
        row=tk.Frame(parent,bg=BG);row.pack(fill="x",padx=10,pady=(0,9));return row

    def table(self,parent,cols,widths,extended=False):
        area=tk.Frame(parent,bg=BG);area.pack(fill="both",expand=True,padx=10,pady=8)
        t=ttk.Treeview(area,columns=cols,show="headings",selectmode="extended" if extended else "browse")
        for col,width in zip(cols,widths):
            t.heading(col,text=col);t.column(col,width=width,minwidth=75,stretch=(col==cols[-1]))
        sb=ttk.Scrollbar(area,orient="vertical",command=t.yview)
        t.configure(yscrollcommand=sb.set);t.pack(side="left",fill="both",expand=True);sb.pack(side="right",fill="y")
        return t

    def submit(self,title,func,on_success):
        self.status.configure(text=title+" in progress...")
        def work():
            try:self.messages.put((title,on_success,func(),None))
            except Exception as exc:self.messages.put((title,on_success,None,str(exc)))
        threading.Thread(target=work,daemon=True).start()

    def poll(self):
        try:
            while True:
                title,callback,value,error=self.messages.get_nowait()
                if error:
                    self.status.configure(text=title+" failed")
                    messagebox.showerror("Diagnostic error",title+":\n"+error)
                else:
                    try:
                        callback(value);self.status.configure(text=title+" complete")
                    except Exception as exc:messagebox.showerror("Display error",str(exc))
        except queue.Empty:pass
        self.after(150,self.poll)

    @staticmethod
    def replace_rows(t,rows):
        t.delete(*t.get_children())
        for row in rows:t.insert("","end",values=row)

    def build_dashboard(self):
        p=self.heading("Dashboard","System overview","CPU, memory, battery and storage information on this PC.")
        self.button(self.toolbar(p),"Refresh diagnostics",self.refresh_dashboard)
        self.metrics=tk.Frame(p,bg=BG);self.metrics.pack(fill="x",padx=10)
        self.metric_labels={}
        for n in ("CPU","Memory","Processes","Battery"):
            f=tk.Frame(self.metrics,bg=PANEL,padx=18,pady=15);f.pack(side="left",fill="x",expand=True,padx=4)
            tk.Label(f,text=n.upper(),fg=MUTED,bg=PANEL).pack(anchor="w")
            label=tk.Label(f,text="--",fg=ACCENT,bg=PANEL,font=(FONT,20,"bold"))
            label.pack(anchor="w");self.metric_labels[n]=label
        tk.Label(p,text="LOCAL DRIVES",fg=FG,bg=BG,font=(FONT,13,"bold")).pack(anchor="w",padx=10,pady=(20,8))
        self.drive_panel=tk.Frame(p,bg=BG);self.drive_panel.pack(fill="both",expand=True,padx=10)
        self.dash_note=tk.Label(p,text="",fg=MUTED,bg=BG,wraplength=940,justify="left")
        self.dash_note.pack(anchor="w",padx=10,pady=12)

    def refresh_dashboard(self):
        self.submit("System diagnostic",m.system_snapshot,self.show_dashboard)

    def show_dashboard(self,d):
        for n,k in (("CPU","cpu_percent"),("Memory","ram_percent")):self.metric_labels[n].configure(text=f"{d[k]:.0f}%")
        self.metric_labels["Processes"].configure(text=str(d["process_count"]))
        b=d["battery_percent"];self.metric_labels["Battery"].configure(text=(f"{b:.0f}%" if b is not None else "N/A"))
        for widget in self.drive_panel.winfo_children():widget.destroy()
        for disk in d["drives"]:
            row=tk.Frame(self.drive_panel,bg=PANEL,padx=14,pady=10);row.pack(fill="x",pady=(0,6))
            used=disk["percent"];color="#ff7f88" if used>=90 else WARN if used>=80 else "#59d6ac"
            tk.Label(row,text=f'{disk["name"]}   {m.human_bytes(disk["free"])} free / {m.human_bytes(disk["total"])} total',
                    bg=PANEL,fg=color,font=(FONT,11,"bold")).pack(anchor="w")
            ttk.Progressbar(row,maximum=100,value=used).pack(fill="x",pady=(8,0))
        self.dash_note.configure(text=f'RAM available: {m.human_bytes(d["ram_available"])}  •  Uptime: {d["uptime_hours"]} hours. Check installed apps if C: is nearly full.')

    def build_processes(self):
        p=self.heading("Processes","Memory-heavy processes","Top running processes by resident memory. No process termination.")
        self.button(self.toolbar(p),"Refresh top processes",lambda:self.submit("Processes",m.top_processes,self.show_processes))
        self.procs=self.table(p,("RAM","CPU","PID","Process"),(140,120,110,650))
    def show_processes(self,items):
        self.replace_rows(self.procs,[(m.human_bytes(x["memory"]),f'{x["cpu"]:.1f}%',x["pid"],x["name"]) for x in items])

    def build_storage(self):
        p=self.heading("Storage Explorer","Large-file explorer","Choose a folder for read-only scanning; files are never deleted here.")
        row=self.toolbar(p)
        self.button(row,"Choose folder",self.choose_folder)
        self.button(row,"Open selected file location",self.open_location)
        self.storage_note=tk.Label(p,text="Start with Downloads, Documents, or a game folder.",bg=BG,fg=MUTED)
        self.storage_note.pack(anchor="w",padx=10)
        self.storage=self.table(p,("Size","Modified","File"),(130,130,680))
    def choose_folder(self):
        folder=filedialog.askdirectory(title="Choose folder to scan",initialdir=str(Path.home()))
        if folder:self.submit("Large-file scan",lambda:m.largest_files(folder),self.show_files)
    def show_files(self,result):
        files,count,truncated=result
        self.storage.delete(*self.storage.get_children());self.file_rows={}
        for item in files:
            key=self.storage.insert("","end",values=(m.human_bytes(item["size"]),item["modified"],item["path"]))
            self.file_rows[key]=item["path"]
        self.storage_note.configure(text=f'{count:,} files checked, {len(files)} displayed'+(" (scan limit reached)" if truncated else ""))
    def open_location(self):
        s=self.storage.selection()
        if not s:return
        path=self.file_rows.get(s[0])
        if not path or not Path(path).exists():return messagebox.showwarning("Unavailable","File no longer exists.")
        if os.name=="nt":
            try:subprocess.Popen(["explorer.exe","/select,",path])
            except OSError as exc:messagebox.showerror("Explorer error",str(exc))

    def build_apps(self):
        p=self.heading("Installed Apps","Installed applications","Sizes are registry estimates, not authoritative disk usage. No uninstall operations.")
        self.button(self.toolbar(p),"Load installed apps",lambda:self.submit("Installed apps",m.installed_apps,self.show_apps))
        self.apps=self.table(p,("Estimated size","Application","Publisher","Version","Location"),(135,280,160,110,370))
    def show_apps(self,items):
        self.replace_rows(self.apps,[(m.human_bytes(x["size"]),x["name"],x["publisher"],x["version"],x["location"]) for x in items])

    def build_startup(self):
        p=self.heading("Startup","Startup inventory","Registry and startup folder inspection only; use Task Manager to disable items.")
        self.button(self.toolbar(p),"Inspect startup entries",lambda:self.submit("Startup",m.startup_entries,self.show_startup))
        self.startup=self.table(p,("Name","Source","Command"),(230,170,690))
    def show_startup(self,items):
        self.replace_rows(self.startup,[(x["name"],x["source"],x["command"]) for x in items])

    def build_cleanup(self):
        p=self.heading("Safe Cleanup","Old temporary-file cleanup","Only files older than 14 days inside your user Temp folder can be recycled.")
        row=self.toolbar(p)
        self.button(row,"Preview old Temp files",self.scan_temp)
        self.button(row,"Move SELECTED to Recycle Bin",self.recycle)
        self.temp_note=tk.Label(p,text="No scan yet. This never empties the Recycle Bin.",fg=MUTED,bg=BG)
        self.temp_note.pack(anchor="w",padx=10)
        self.temp=self.table(p,("Size","Modified","Temp file"),(130,130,750),extended=True)
        tk.Label(p,text="Downloads, projects, Windows folders and new temporary files are excluded.",
                 bg=BG,fg=MUTED).pack(anchor="w",padx=10,pady=8)
    def scan_temp(self):self.submit("Temp preview",m.temp_candidates,self.show_temp)
    def show_temp(self,result):
        files,count,truncated=result
        self.temp.delete(*self.temp.get_children());self.temp_rows={}
        for item in files[:1000]:
            key=self.temp.insert("","end",values=(m.human_bytes(item["size"]),item["modified"],item["path"]))
            self.temp_rows[key]=item
        self.temp_note.configure(text=f'{len(files)} candidates ({m.human_bytes(sum(x["size"] for x in files))}), {count:,} checked. Nothing changed.')
    def recycle(self):
        selected=[self.temp_rows[x] for x in self.temp.selection() if x in self.temp_rows]
        if not selected:return messagebox.showinfo("Select files","Choose one or more old Temp files first.")
        size=m.human_bytes(sum(x["size"] for x in selected))
        if not messagebox.askyesno("Review cleanup",f'Move {len(selected)} selected files ({size}) to Recycle Bin?\n\nThis does not immediately free disk space.'):return
        if simpledialog.askstring("Final confirmation","Type RECYCLE to confirm:")!="RECYCLE":return
        self.submit("Approved temp recycling",lambda:m.recycle_selected_temp_files([x["path"] for x in selected]),self.cleanup_done)
    def cleanup_done(self,result):
        moved,errors=result
        messagebox.showinfo("Cleanup result",f'{len(moved)} moved to Recycle Bin; {len(errors)} skipped.\n\nReview Recycle Bin before emptying it.')
        self.scan_temp()

    def build_health(self):
        p=self.heading("Health & Reports","Disk health and reports","Windows storage provider status is not a full SMART assessment.")
        row=self.toolbar(p)
        self.button(row,"Check disk status",lambda:self.submit("Disk health",m.disk_health,self.show_health))
        self.button(row,"Export local JSON report",self.export_report)
        self.button(row,"Open Reliability Monitor",self.open_reliability)
        self.health=tk.Text(p,bg=PANEL,fg=FG,insertbackground=FG,font=("Consolas",10),wrap="word",padx=14,pady=12)
        self.health.pack(fill="both",expand=True,padx=10,pady=10)
        self.show_text("Disk status not queried.\n\nRAID controllers may hide SSD SMART details. Never change BIOS RAID mode simply for maintenance.")
    def show_text(self,text):
        self.health.configure(state="normal");self.health.delete("1.0","end")
        self.health.insert("end",text);self.health.configure(state="disabled")
    def show_health(self,result):
        note,drives=result;self.show_text(note+"\n\n"+json.dumps(drives,indent=2))
    def export_report(self):
        path=filedialog.asksaveasfilename(title="Save local diagnostic report",defaultextension=".json",
                                          filetypes=[("JSON","*.json")],initialfile="AI_Laptop_Manager_Report.json")
        if not path:return
        self.submit("Local report",m.report_dict,lambda d:self.save_report(path,d))
    def save_report(self,path,data):
        try:
            Path(path).write_text(json.dumps(data,indent=2),encoding="utf-8")
            messagebox.showinfo("Saved","Report saved locally. Review personal paths and startup commands before sharing.")
        except OSError as exc:messagebox.showerror("Save failed",str(exc))
    def open_reliability(self):
        if os.name!="nt":return messagebox.showinfo("Windows only","Reliability Monitor is a Windows tool.")
        try:subprocess.Popen(["perfmon.exe","/rel"])
        except OSError as exc:messagebox.showerror("Unavailable",str(exc))

if __name__=="__main__":
    LaptopManager().mainloop()

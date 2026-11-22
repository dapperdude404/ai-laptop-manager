"""Smart Control Center V2.5 — local-first, explicit-action Tkinter panels.

The user controls all changes. Other laptop reports are imported locally by
consent; application uninstall remains via Windows Settings.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import psutil
import maintenance as m
from smart_engine import profile_from_snapshot, advice, compare_profiles, validate_profile, profile_json
from power_center import (diagnostic_snapshot, list_power_plans, read_power_blockers,
                          read_sleep_capabilities, change_power_plan, battery_report)
from ui_compat import BG, SURFACE, SURFACE2, ACCENT, FG, MUTED, label, button

class SmartCenterMixin:
    def add_smart_center(self):
        root = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(root, text="Smart Control Center")
        self.headline(root, "SMART CONTROL CENTER 2.5",
                      "Real measurements • Explainable recommendations • Undoable power plans • No cloud uploads")
        self.smart_tabs = ttk.Notebook(root)
        self.smart_tabs.pack(fill="both", expand=True, padx=10, pady=(4,10))
        for name, build in (
            ("Laptop Insights", self._smart_insights),
            ("Power & Battery", self._smart_power),
            ("Application Manager", self._smart_apps_page),
            ("Compare Laptops", self._smart_compare),
        ):
            pane = tk.Frame(self.smart_tabs, bg=BG)
            self.smart_tabs.add(pane, text=name)
            build(pane)
        self.current_profile = None
        self.smart_peers = []

    def _sc_bar(self, page):
        pane = tk.Frame(page, bg=BG)
        pane.pack(fill="x", padx=10, pady=(4,10))
        return pane

    def _sc_text(self, page, initial=""):
        box = tk.Text(page, bg=SURFACE, fg=FG, relief="flat",
                      font=("Consolas",10), padx=14, pady=12, wrap="word")
        box.pack(fill="both", expand=True, padx=10, pady=10)
        box.insert("1.0", initial)
        box.config(state="disabled")
        return box

    def _sc_write(self, box, text):
        box.config(state="normal")
        box.delete("1.0","end")
        box.insert("1.0",text)
        box.config(state="disabled")

    def _smart_insights(self, page):
        self.headline(page, "Explainable laptop intelligence",
                      "Every recommendation shows measured evidence, uncertainty and a safe next step.")
        row = self._sc_bar(page)
        button(row, "Analyze current laptop", self.sc_analyze).pack(side="left")
        button(row, "Open Windows storage", self.sc_open_storage).pack(side="left", padx=9)
        self.sc_insight_text = self._sc_text(page,
            "No diagnostic result yet. Click Analyze current laptop.\n"
            "No performance percentage or hardware-health claim is fabricated.")

    def sc_analyze(self):
        def collect():
            snap = m.system_snapshot()
            profile = profile_from_snapshot(
                snap, logical_cores=psutil.cpu_count(logical=True),
                ram_total_bytes=psutil.virtual_memory().total)
            return profile, advice(profile)
        self.job("Smart laptop analysis", collect, self.sc_show_insights)

    def sc_show_insights(self, payload):
        profile, findings = payload
        self.current_profile = profile
        lines=["INTELLIGENCE REPORT — SNAPSHOT, NOT A STRESS TEST",
               "="*64,
               f"CPU logical cores: {profile['cpu_logical_cores']:.0f}",
               f"Installed RAM: {profile['ram_gib']:.1f} GiB",
               f"Windows C: drive free: {profile['system_drive_free_pct']:.1f}%",
               f"CPU snapshot: {profile['cpu_utilization_pct']:.1f}%",
               f"RAM snapshot: {profile['ram_utilization_pct']:.1f}%",
               ""]
        for finding in findings:
            lines.extend([f"[{finding['severity']}] {finding['title']}",
                          "Evidence: "+finding["evidence"],
                          "Recommended: "+finding["recommendation"],
                          "Certainty: "+finding["certainty"],""])
        lines.append("No automatic registry, service, driver, RAM-cache or security changes.")
        self._sc_write(self.sc_insight_text, "\n".join(lines))

    @staticmethod
    def sc_open_storage():
        if os.name=="nt":
            os.startfile("ms-settings:storagesense")
        else:
            messagebox.showinfo("Windows-only","This link requires Windows.")

    def _smart_power(self, page):
        self.headline(page, "Power Cycle Lab",
                      "Examine charging, CPU clocks, sleep blockers and power plans. Watts/amps are unknown without sensors.")
        row=self._sc_bar(page)
        button(row,"Refresh power data",self.sc_refresh_power).pack(side="left")
        button(row,"Sleep blockers",self.sc_power_blockers).pack(side="left",padx=6)
        button(row,"Sleep capabilities",self.sc_power_states).pack(side="left",padx=6)
        button(row,"Create battery report",self.sc_battery_report).pack(side="left",padx=6)
        self.sc_power_text = self._sc_text(page,"Select Refresh power data. No power plan has been changed.")
        row2=self._sc_bar(page)
        label(row2,"Available power plans",color=ACCENT).pack(side="left",padx=(0,10))
        self.sc_plan_selected = tk.StringVar(value="")
        self.sc_plan_box = ttk.Combobox(row2,textvariable=self.sc_plan_selected,
                                         values=[],width=55,state="readonly")
        self.sc_plan_box.pack(side="left",padx=5)
        button(row2,"Apply selected (confirm)",self.sc_apply_plan).pack(side="left",padx=4)
        button(row2,"Undo last plan change",self.sc_revert_plan).pack(side="left",padx=4)
        self.sc_power_choices = {}
        self.sc_prev_plan = None

    def sc_refresh_power(self):
        def collect():
            return diagnostic_snapshot(), list_power_plans()
        self.job("Read power status",collect,self.sc_show_power)

    def sc_show_power(self, payload):
        snapshot, plans=payload
        self.sc_power_choices={}
        labels=[]
        for p in plans["plans"]:
            display=("* ACTIVE * " if p["active"] else "")+p["name"]+" — "+p["guid"]
            labels.append(display)
            self.sc_power_choices[display]=p["guid"]
        self.sc_plan_box.configure(values=labels)
        if labels:
            index=next((i for i,p in enumerate(plans["plans"]) if p["active"]),0)
            self.sc_plan_box.current(index)
        lines=["POWER & BATTERY — ON-DEMAND SNAPSHOT",
               f"Battery charge: {snapshot['charge_percent'] if snapshot['charge_percent'] is not None else 'N/A'}%",
               f"AC connected: {snapshot['plugged_in'] if snapshot['plugged_in'] is not None else 'Unknown'}",
               f"CPU current clock: {snapshot['cpu_frequency_mhz']} MHz",
               "Current draw (A): NOT MEASURED",
               "Electrical power (W): NOT MEASURED",
               "Available plan count: "+str(len(labels)), "",
               snapshot["explanation"], "",
               "Power reports may need administrator access. Change only one power plan at a time."]
        self._sc_write(self.sc_power_text,"\n".join(lines))

    def sc_power_blockers(self):
        self.job("Query sleep blockers",read_power_blockers,
                 lambda result:self._sc_write(self.sc_power_text,
                     "POWERCFG /REQUESTS (read-only)\n\n"+result))

    def sc_power_states(self):
        self.job("Query sleep capabilities",read_sleep_capabilities,
                 lambda result:self._sc_write(self.sc_power_text,
                     "POWERCFG /A (read-only)\n\n"+result))

    def sc_apply_plan(self):
        selection=self.sc_plan_selected.get()
        guid=self.sc_power_choices.get(selection)
        if not guid:
            messagebox.showinfo("Select plan","Refresh and choose an available power plan first.")
            return
        if not messagebox.askyesno("Confirm Windows power plan change",
                "Apply this Windows power plan?\n\n"+selection+
                "\n\nPower consumption, thermals and battery life may change. "
                "An undo button will be available during this session."):
            return
        self.job("Apply user-approved power plan",
                 lambda:change_power_plan(guid,confirmed=True),
                 self.sc_show_changed_plan)

    def sc_show_changed_plan(self, outcome):
        if outcome["changed"]:
            self.sc_prev_plan=outcome["previous"]
        messagebox.showinfo("Power plan", "Power plan applied and verified." if outcome["changed"]
                            else "That power plan is already active.")
        self.sc_refresh_power()

    def sc_revert_plan(self):
        old=self.sc_prev_plan
        if not old:
            messagebox.showinfo("No previous plan","No power plan change to undo in this session.")
            return
        if not messagebox.askyesno("Revert power plan",
                "Restore previously active Windows power plan?\n\n"+old):
            return
        self.job("Restore user-approved power plan",
                 lambda:change_power_plan(old,confirmed=True),
                 self.sc_show_revert)

    def sc_show_revert(self, outcome):
        self.sc_prev_plan=None
        messagebox.showinfo("Power plan", "Previous power plan restored and verified.")
        self.sc_refresh_power()

    def sc_battery_report(self):
        path=filedialog.asksaveasfilename(title="Save new battery report locally",
                 defaultextension=".html",filetypes=[("HTML report","*.html")],
                 initialfile="AI_Laptop_Manager_Battery_Report.html")
        if not path:
            return
        if not messagebox.askyesno("Confirm battery report","Create a local battery report here?\n\n"+
                                   path+"\n\nThe report can contain usage history. It will not be uploaded."):
            return
        self.job("Generate local battery report",
                 lambda:battery_report(path,confirmed=True),
                 lambda result:messagebox.showinfo("Report ready","Saved locally:\n"+result))

    def _smart_apps_page(self,page):
        self.headline(page,"Application manager",
                      "Review installed programs and their reported sizes. Uninstall through Windows Settings.")
        bar=self._sc_bar(page)
        button(bar,"Load installed applications",self.sc_load_apps).pack(side="left")
        button(bar,"Open uninstall settings",self.sc_open_apps).pack(side="left",padx=6)
        self.sc_app_filter=tk.StringVar()
        label(bar,"Search:",color=MUTED).pack(side="left",padx=(12,3))
        entry=tk.Entry(bar,textvariable=self.sc_app_filter,bg=SURFACE2,fg=FG,
                       insertbackground=FG,relief="flat",width=24)
        entry.pack(side="left")
        self.sc_app_filter.trace_add("write",lambda *_:self.sc_filter_apps())
        self.sc_apps_tree=self.tree(page,("Size estimate","Application","Publisher","Install location"),
                                   (130,300,220,430))
        self.sc_apps_note=label(page,"Sizes are Windows registry estimates, not measured usage. "
                            "Never manually delete Program Files or installer EXEs.",color=MUTED)
        self.sc_apps_note.pack(anchor="w",padx=10,pady=4)
        self.sc_app_data=[]

    def sc_load_apps(self):
        self.job("Inventory installed apps",m.installed_apps,self.sc_show_apps)

    def sc_show_apps(self,apps):
        self.sc_app_data=apps
        self.sc_filter_apps()

    def sc_filter_apps(self):
        if not hasattr(self,"sc_apps_tree"):
            return
        term=self.sc_app_filter.get().strip().casefold()
        rows=[(m.human_bytes(a["size"]),a["name"],a["publisher"],a["location"])
              for a in self.sc_app_data if term in (a["name"]+" "+a["publisher"]).casefold()]
        self.replace_rows(self.sc_apps_tree,rows[:1000])
        self.sc_apps_note.config(text=f"{len(rows)} matching installed entries (first 1,000 shown). "
                             "Sizes are registry estimates. Uninstall only through Windows Settings.")

    @staticmethod
    def sc_open_apps():
        if os.name=="nt":
            os.startfile("ms-settings:appsfeatures")
        else:
            messagebox.showinfo("Windows-only","Windows Settings is unavailable.")

    def _smart_compare(self,page):
        self.headline(page,"Consented laptop comparison",
                      "Export only five numeric metrics. Import two to four reports from consenting laptop owners.")
        bar=self._sc_bar(page)
        button(bar,"Capture my profile",self.sc_analyze).pack(side="left")
        button(bar,"Export anonymous JSON",self.sc_export_profile).pack(side="left",padx=5)
        button(bar,"Import 2–4 peers",self.sc_import_peers).pack(side="left",padx=5)
        button(bar,"Compare measurements",self.sc_compare).pack(side="left",padx=5)
        self.sc_compare_text=self._sc_text(page,
            "Comparisons happen on this laptop only. No report is uploaded.\n"
            "No simulated machine data are presented as real results.\n"
            "Small samples are not meaningful performance benchmarks.")

    def sc_export_profile(self):
        if self.current_profile is None:
            messagebox.showinfo("Collect first","Use Capture my profile or Analyze current laptop.")
            return
        path=filedialog.asksaveasfilename(defaultextension=".json",
              initialfile="anonymous_laptop_profile.json",filetypes=[("JSON","*.json")])
        if not path:
            return
        if not messagebox.askyesno("Privacy check",
                "Export only 5 numeric performance/capacity values?\n"
                "No hostname, user ID, serial, filenames or device identifier will be included."):
            return
        try:
            with open(path,"x",encoding="utf-8") as f:
                f.write(profile_json(self.current_profile))
        except (OSError,ValueError) as exc:
            messagebox.showerror("Export failed",str(exc))
            return
        messagebox.showinfo("Saved","Anonymous metrics saved locally. Share only with consent.")

    def sc_import_peers(self):
        files=filedialog.askopenfilenames(title="Select 2 to 4 consented laptop reports",
                      filetypes=[("Anonymized JSON","*.json")])
        if not files:
            return
        if not 2 <= len(files) <= 4:
            messagebox.showwarning("Need 2 to 4 reports","Select reports from two to four laptops.")
            return
        try:
            reports=[]
            for filepath in files:
                if Path(filepath).stat().st_size > 20000:
                    raise ValueError("Profile too large; only compact anonymous JSON is supported.")
                with open(filepath,encoding="utf-8") as f:
                    reports.append(validate_profile(json.load(f)))
        except (OSError,ValueError,TypeError,KeyError) as exc:
            messagebox.showerror("Invalid peer profile",str(exc))
            return
        self.smart_peers=reports
        self._sc_write(self.sc_compare_text,f"Imported {len(reports)} anonymized profiles locally.\n"
                       "Press Compare measurements to view per-metric medians.")

    def sc_compare(self):
        if self.current_profile is None:
            messagebox.showinfo("Collect first","Capture this laptop's profile first.")
            return
        try:
            result=compare_profiles(self.current_profile,self.smart_peers)
        except ValueError as exc:
            messagebox.showwarning("More data needed",str(exc))
            return
        lines=[f"CONSENTED PEER COMPARISON (n={result['count']})",
               "Metric | This laptop | Peer median | Peer range","-"*72]
        for r in result["rows"]:
            lines.append(f"{r['metric']:<26} {r['this_laptop']:<12} {r['peer_median']:<12} "
                         f"{r['peer_min']}–{r['peer_max']}")
        lines.extend(["",result["privacy"],result["limitations"]])
        self._sc_write(self.sc_compare_text,"\n".join(lines))

"""Local Windows maintenance engine. No telemetry; writes only by explicit recycle call."""
import os, sys, stat, time, json, heapq, platform, tempfile, subprocess
from pathlib import Path
from datetime import datetime
import psutil
APP_VERSION="1.0.0"
TEMP_MIN_AGE_DAYS=14
MAX_SCAN_FILES=180000

def human_bytes(value):
    if value is None: return "Unknown"
    n=float(value)
    for unit in ("B","KiB","MiB","GiB","TiB"):
        if abs(n)<1024 or unit=="TiB": return f"{n:.0f} {unit}" if unit=="B" else f"{n:.1f} {unit}"
        n/=1024
    return "Unknown"

def drives():
    result=[]; seen=set()
    for d in psutil.disk_partitions(all=False):
        if d.mountpoint.lower() in seen: continue
        seen.add(d.mountpoint.lower())
        try: u=psutil.disk_usage(d.mountpoint)
        except (OSError,PermissionError): continue
        result.append(dict(name=d.mountpoint,device=d.device,filesystem=d.fstype,total=u.total,used=u.used,free=u.free,percent=u.percent))
    return sorted(result,key=lambda d:d["name"])

def system_snapshot():
    m=psutil.virtual_memory()
    try: b=psutil.sensors_battery()
    except (OSError,RuntimeError): b=None
    return dict(time=datetime.now().astimezone().isoformat(),computer=platform.node(),os=platform.platform(),
        cpu_model=platform.processor() or "Unknown",cpu_percent=psutil.cpu_percent(interval=.15),
        logical_cpus=psutil.cpu_count(),physical_cpus=psutil.cpu_count(logical=False),
        ram_used=m.used,ram_total=m.total,ram_available=m.available,ram_percent=m.percent,
        process_count=len(psutil.pids()),uptime_hours=round((time.time()-psutil.boot_time())/3600,1),
        battery_percent=b.percent if b else None,battery_plugged=b.power_plugged if b else None,drives=drives())

def _is_reparse_or_link(path):
    try:
        st=Path(path).lstat()
        return stat.S_ISLNK(st.st_mode) or bool(getattr(st,"st_file_attributes",0)&0x400)
    except OSError: return True

def _strict_descendant(child,parent):
    try:
        c=Path(os.path.abspath(child)); p=Path(os.path.abspath(parent))
        return c!=p and c.is_relative_to(p)
    except (ValueError,TypeError): return False

def largest_files(root,*,limit=100,max_files=MAX_SCAN_FILES):
    root=Path(root).expanduser().resolve(strict=True)
    if not root.is_dir(): raise NotADirectoryError(str(root))
    heap=[]; count=0; truncated=False; i=0
    for current,folders,names in os.walk(root,followlinks=False):
        folders[:]=[f for f in folders if not _is_reparse_or_link(Path(current)/f)]
        for name in names:
            if count>=max_files: truncated=True;break
            count+=1; p=Path(current)/name
            if _is_reparse_or_link(p):continue
            try: st=p.stat(follow_symlinks=False)
            except OSError:continue
            if not stat.S_ISREG(st.st_mode):continue
            item=dict(path=str(p),size=st.st_size,modified=datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d"))
            i+=1; entry=(st.st_size,i,item)
            if len(heap)<limit:heapq.heappush(heap,entry)
            elif st.st_size>heap[0][0]:heapq.heapreplace(heap,entry)
        if truncated:break
    return [x[2] for x in sorted(heap,reverse=True)],count,truncated

def get_user_temp_root():
    if os.name=="nt":
        local=os.environ.get("LOCALAPPDATA")
        if not local: raise RuntimeError("LOCALAPPDATA missing")
        root=(Path(local)/"Temp").resolve(strict=True)
        if not root.is_dir():raise RuntimeError("User Temp directory missing")
        return root
    return Path(tempfile.gettempdir()).resolve(strict=True)

def temp_candidates(*,min_age_days=TEMP_MIN_AGE_DAYS,max_files=MAX_SCAN_FILES,root=None):
    base=Path(root).resolve(strict=True) if root else get_user_temp_root()
    cutoff=time.time()-min_age_days*86400; items=[];count=0;truncated=False
    for current,folders,names in os.walk(base,followlinks=False):
        folders[:]=[f for f in folders if not _is_reparse_or_link(Path(current)/f)]
        for name in names:
            if count>=max_files:truncated=True;break
            count+=1;p=Path(current)/name
            if _is_reparse_or_link(p) or not _strict_descendant(p,base):continue
            try:st=p.stat(follow_symlinks=False)
            except OSError:continue
            if not stat.S_ISREG(st.st_mode) or st.st_mtime>cutoff:continue
            items.append(dict(path=str(p),size=st.st_size,modified=datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d")))
        if truncated:break
    return sorted(items,key=lambda x:x["size"],reverse=True),count,truncated

def recycle_selected_temp_files(paths,*,min_age_days=TEMP_MIN_AGE_DAYS,root=None):
    from send2trash import send2trash
    base=Path(root).resolve(strict=True) if root else get_user_temp_root()
    cutoff=time.time()-min_age_days*86400;moved=[];failures=[]
    for name in dict.fromkeys(paths):
        p=Path(name)
        try:
            if not _strict_descendant(p,base):raise ValueError("Outside permitted Temp directory")
            if _is_reparse_or_link(p):raise ValueError("Link or junction")
            st=p.stat(follow_symlinks=False)
            if not stat.S_ISREG(st.st_mode):raise ValueError("Not a regular file")
            if st.st_mtime>cutoff:raise ValueError("File too recent")
            if not _strict_descendant(p.resolve(strict=True),base):raise ValueError("Redirected outside Temp")
            send2trash(str(p));moved.append(str(p))
        except (OSError,ValueError,RuntimeError) as exc: failures.append(f"{p}: {exc}")
    return moved,failures

def top_processes(*,limit=75):
    rows=[]
    for proc in psutil.process_iter(attrs=["pid","name","memory_info","cpu_percent"]):
        try:
            i=proc.info
            rows.append(dict(pid=i["pid"],name=i.get("name") or "Unknown",
                memory=i["memory_info"].rss if i.get("memory_info") else 0,cpu=i.get("cpu_percent") or 0))
        except (OSError,psutil.Error):pass
    return sorted(rows,key=lambda x:x["memory"],reverse=True)[:limit]

def installed_apps():
    if os.name!="nt":return []
    import winreg
    base=r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    entries={}
    for hive,scope in ((winreg.HKEY_LOCAL_MACHINE,"Machine"),(winreg.HKEY_CURRENT_USER,"User")):
        for view in (winreg.KEY_WOW64_64KEY,winreg.KEY_WOW64_32KEY):
            try:key=winreg.OpenKey(hive,base,0,winreg.KEY_READ|view)
            except OSError:continue
            with key:
                for j in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        with winreg.OpenKey(key,winreg.EnumKey(key,j)) as sub:
                            def val(n):
                                try:return winreg.QueryValueEx(sub,n)[0]
                                except OSError:return None
                            name=val("DisplayName")
                            if not name or val("SystemComponent")==1:continue
                            publisher=val("Publisher") or "Unknown"
                            version=val("DisplayVersion") or ""
                            size_kib=val("EstimatedSize")
                            size=size_kib*1024 if isinstance(size_kib,int) and size_kib>0 else None
                            row=dict(name=str(name),publisher=str(publisher),version=str(version),size=size,
                                scope=scope,location=str(val("InstallLocation") or ""))
                            entries[(str(name).casefold(),str(publisher).casefold(),str(version).casefold())]=row
                    except (OSError,ValueError,TypeError):continue
    return sorted(entries.values(),key=lambda a:(a["size"] is None,-(a["size"] or 0),a["name"].casefold()))

def startup_entries():
    if os.name!="nt":return []
    import winreg
    result=[];key_name=r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
    for hive,scope in ((winreg.HKEY_LOCAL_MACHINE,"Machine"),(winreg.HKEY_CURRENT_USER,"User")):
        for view in (winreg.KEY_WOW64_64KEY,winreg.KEY_WOW64_32KEY):
            try:key=winreg.OpenKey(hive,key_name,0,winreg.KEY_READ|view)
            except OSError:continue
            with key:
                for i in range(winreg.QueryInfoKey(key)[1]):
                    try:
                        name,cmd,_=winreg.EnumValue(key,i)
                        result.append(dict(name=name,source=scope+" Run key",command=str(cmd)))
                    except OSError:pass
    for env,tail in (("APPDATA","Microsoft/Windows/Start Menu/Programs/Startup"),
                     ("PROGRAMDATA","Microsoft/Windows/Start Menu/Programs/StartUp")):
        root=os.environ.get(env)
        if not root:continue
        folder=Path(root)/tail
        if folder.is_dir():
            try:
                for p in folder.iterdir():result.append(dict(name=p.name,source="Startup folder",command=str(p)))
            except OSError:pass
    return sorted({(r["name"].casefold(),r["command"].casefold()):r for r in result}.values(),key=lambda r:r["name"].casefold())

def disk_health():
    if os.name!="nt":return "Available on Windows only",[]
    cmd="Get-PhysicalDisk | Select FriendlyName,HealthStatus,OperationalStatus,MediaType | ConvertTo-Json -Compress"
    try:
        p=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",cmd],
            capture_output=True,text=True,timeout=14,creationflags=0x08000000)
        if p.returncode or not p.stdout.strip():return "Windows storage provider returned no data",[]
        data=json.loads(p.stdout)
        return "Windows provider status, not a complete SMART test",data if isinstance(data,list) else [data]
    except (OSError,subprocess.TimeoutExpired,ValueError):return "Health data unavailable",[]

def report_dict():
    return dict(version=APP_VERSION,snapshot=system_snapshot(),apps=installed_apps(),
        startup=startup_entries(),disk_health={"note":"Read-only Windows provider status","results":disk_health()[1]})

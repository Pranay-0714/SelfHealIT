"""PC Health Scanner (READ-ONLY). Collects real data via psutil, ctypes, and Windows
built-in tools. Nothing here changes the system."""
import platform, subprocess, time, datetime, os, ctypes
import psutil

def _run(cmd, timeout=8):
    """Run a fixed, read-only command. Returns text or None."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() or None
    except Exception:
        return None

def get_gpu_details():
    """Retrieve detailed GPU information via PowerShell CIM Win32_VideoController."""
    if platform.system() != "Windows":
        return [{"name": "unavailable (Windows only)", "memory_gb": 0, "driver": "N/A", "status": "N/A"}]
    
    cmd = [
        "powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_VideoController | Select-Object -Property Name, AdapterRAM, DriverVersion, Status | ConvertTo-Json"
    ]
    raw = _run(cmd, timeout=8)
    if not raw:
        return [{"name": "Standard Display Adapter", "memory_gb": 0, "driver": "Unknown", "status": "OK"}]
    
    try:
        import json
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        gpus = []
        for g in data:
            bytes_ram = g.get("AdapterRAM") or 0
            if isinstance(bytes_ram, int) and bytes_ram > 0:
                ram_gb = round(bytes_ram / (1024**3), 2)
            else:
                ram_gb = 0.0
            gpus.append({
                "name": g.get("Name") or "Unknown GPU",
                "memory_gb": ram_gb,
                "driver": g.get("DriverVersion") or "Unknown",
                "status": g.get("Status") or "OK"
            })
        return gpus if gpus else [{"name": "Unknown GPU", "memory_gb": 0, "driver": "Unknown", "status": "OK"}]
    except Exception:
        return [{"name": raw[:60], "memory_gb": 0, "driver": "Unknown", "status": "OK"}]

def get_gpu():
    """Backward compatible GPU string."""
    gpus = get_gpu_details()
    return "; ".join(f"{g['name']} ({g['memory_gb']} GB VRAM)" if g['memory_gb'] > 0 else g['name'] for g in gpus)

def get_startup_apps():
    """Enumerate Windows Run registry keys for startup apps."""
    apps = []
    if platform.system() != "Windows":
        return apps
    try:
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, r"Software\Microsoft\Windows\CurrentVersion\Run") as k:
                    for i in range(winreg.QueryInfoKey(k)[1]):
                        try:
                            name, val, _ = winreg.EnumValue(k, i)
                            apps.append({"name": name, "command": str(val)})
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        pass
    return apps

def get_wifi():
    """Query Wi-Fi adapter details via netsh wlan."""
    if platform.system() != "Windows":
        return {"available": False}
    out = _run(["netsh", "wlan", "show", "interfaces"], timeout=5)
    info = {"available": bool(out)}
    for line in (out or "").splitlines():
        if ":" in line:
            k, v = [x.strip() for x in line.split(":", 1)]
            if k in ("SSID", "Signal", "Radio type", "Authentication", "State", "Description"):
                info[k] = v
    return info

def get_battery():
    """Retrieve laptop battery and power status if available."""
    try:
        b = psutil.sensors_battery()
        if b is None:
            return {"present": False, "plugged": True, "percent": 100}
        return {
            "present": True,
            "percent": round(b.percent, 1),
            "plugged": b.power_plugged,
            "seconds_left": b.secsleft if b.secsleft != psutil.POWER_TIME_UNLIMITED else None
        }
    except Exception:
        return {"present": False, "plugged": True, "percent": 100}

def get_swap_safe():
    """Safely fetch swap / pagefile memory without PDH performance counter crashes."""
    try:
        sw = psutil.swap_memory()
        return {
            "total_gb": round(sw.total / (1024**3), 1),
            "used_gb": round(sw.used / (1024**3), 1),
            "free_gb": round(sw.free / (1024**3), 1),
            "percent": round(sw.percent, 1)
        }
    except Exception:
        return {
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "percent": 0.0,
            "note": "Performance counter unavailable"
        }

def get_hung_applications():
    """Detect non-responsive Windows applications using user32.IsHungAppWindow."""
    hung = []
    if platform.system() != "Windows":
        return hung
    try:
        user32 = ctypes.windll.user32
        
        def enum_cb(hwnd, extra):
            if user32.IsWindowVisible(hwnd) and user32.IsHungAppWindow(hwnd):
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                p_id = pid.value
                title_buf = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, title_buf, 512)
                title = title_buf.value or "Hung Application Window"
                
                try:
                    p = psutil.Process(p_id)
                    p_name = p.name()
                except Exception:
                    p_name = "Unknown"
                    
                if not any(h["pid"] == p_id for h in hung):
                    hung.append({
                        "pid": p_id,
                        "name": p_name,
                        "title": title,
                        "reason": "Application window is not responding to Windows messages"
                    })
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    except Exception:
        pass
    return hung

def get_windows_defender_status():
    """Query Windows Defender status using PowerShell Get-MpComputerStatus."""
    if platform.system() != "Windows":
        return {"available": False, "antivirus_enabled": False, "realtime_enabled": False}
    cmd = [
        "powershell", "-NoProfile", "-Command",
        "Get-MpComputerStatus | Select-Object -Property AntivirusEnabled, RealTimeProtectionEnabled, AntivirusSignatureAge, AntivirusSignatureVersion, QuickScanAge, AMServiceEnabled | ConvertTo-Json"
    ]
    raw = _run(cmd, timeout=8)
    if not raw:
        return {"available": False, "antivirus_enabled": False, "realtime_enabled": False}
    try:
        import json
        data = json.loads(raw)
        if isinstance(data, dict):
            return {
                "available": True,
                "antivirus_enabled": bool(data.get("AntivirusEnabled", False)),
                "realtime_enabled": bool(data.get("RealTimeProtectionEnabled", False)),
                "service_enabled": bool(data.get("AMServiceEnabled", False)),
                "signature_age_days": data.get("AntivirusSignatureAge") if data.get("AntivirusSignatureAge", 4294967295) < 36500 else None,
                "signature_version": str(data.get("AntivirusSignatureVersion", "Unknown")),
                "quick_scan_age_days": data.get("QuickScanAge") if data.get("QuickScanAge", 4294967295) < 36500 else None
            }
    except Exception:
        pass
    return {"available": False, "antivirus_enabled": False, "realtime_enabled": False}

SUSPICIOUS_DIRS = ("\\temp\\", "\\appdata\\local\\temp", "/tmp/", "\\downloads\\")

def find_suspicious(procs):
    """Heuristic indicators only - NOT an antivirus verdict."""
    hits = []
    for p in procs:
        exe = (p.get("exe") or "").lower()
        if exe and any(d in exe for d in SUSPICIOUS_DIRS):
            hits.append({
                "pid": p["pid"],
                "name": p["name"],
                "reason": "Runs from a temp/downloads folder",
                "exe": exe
            })
    return hits

def scan():
    """Perform a comprehensive, read-only PC health scan."""
    psutil.cpu_percent(None)
    time.sleep(0.4)
    cpu_percent = psutil.cpu_percent(None)
    per_cpu = psutil.cpu_percent(percpu=True)
    
    vm = psutil.virtual_memory()
    sw = get_swap_safe()
    
    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            u = psutil.disk_usage(part.mountpoint)
            disks.append({
                "mount": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": round(u.total / (1024**3), 1),
                "used_gb": round(u.used / (1024**3), 1),
                "free_gb": round(u.free / (1024**3), 1),
                "percent": u.percent
            })
        except Exception:
            pass
            
    procs = []
    for p in psutil.process_iter(["pid", "name", "exe", "memory_percent", "cpu_percent", "status"]):
        try:
            info = p.info
            mem_pct = round(info.get("memory_percent") or 0, 2)
            procs.append({
                "pid": info["pid"],
                "name": info["name"] or "Unknown",
                "exe": info.get("exe") or "",
                "status": info.get("status") or "running",
                "mem_percent": mem_pct,
                "cpu_percent": round(info.get("cpu_percent") or 0, 1)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
            
    top_mem = sorted(procs, key=lambda x: x["mem_percent"], reverse=True)[:10]
    top_cpu = sorted(procs, key=lambda x: x["cpu_percent"], reverse=True)[:10]
    
    try:
        conns = psutil.net_connections(kind="inet")
        net = {
            "total": len(conns),
            "established": sum(1 for c in conns if c.status == "ESTABLISHED"),
            "listening": sum(1 for c in conns if c.status == "LISTEN"),
            "time_wait": sum(1 for c in conns if c.status == "TIME_WAIT")
        }
    except Exception:
        net = {"total": 0, "established": None, "listening": None, "note": "needs admin rights for deep connection audit"}
        
    freq = psutil.cpu_freq()
    gpu_details = get_gpu_details()
    gpu_str = get_gpu()
    hung_apps = get_hung_applications()
    defender_info = get_windows_defender_status()
    suspicious = find_suspicious(procs)
    
    data = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.machine(),
            "uptime_hours": round((time.time() - psutil.boot_time()) / 3600, 1)
        },
        "cpu": {
            "name": platform.processor() or "Generic x86_64",
            "physical_cores": psutil.cpu_count(logical=False) or 2,
            "logical_cores": psutil.cpu_count(logical=True) or 4,
            "usage_percent": cpu_percent,
            "per_cpu_percent": per_cpu,
            "max_mhz": round(freq.max) if freq and freq.max else None,
            "current_mhz": round(freq.current) if freq and freq.current else None
        },
        "ram": {
            "total_gb": round(vm.total / (1024**3), 1),
            "available_gb": round(vm.available / (1024**3), 1),
            "used_gb": round((vm.total - vm.available) / (1024**3), 1),
            "percent": vm.percent,
            "swap_percent": sw.get("percent", 0.0),
            "swap": sw
        },
        "gpu": gpu_str,
        "gpus": gpu_details,
        "disks": disks,
        "process_count": len(procs),
        "top_processes": top_mem,
        "top_cpu_processes": top_cpu,
        "hung_apps": hung_apps,
        "startup_apps": get_startup_apps(),
        "wifi": get_wifi(),
        "battery": get_battery(),
        "network": net,
        "defender": defender_info,
        "suspicious": suspicious
    }
    
    data["findings"] = analyze(data)
    data["health_score"] = calculate_health_score(data)
    return data

def _f(sev, title, cause, conseq, fix, recovery, action=None, target_pid=None):
    return {
        "severity": sev,
        "problem": title,
        "cause": cause,
        "consequence": conseq,
        "solution": fix,
        "recovery": recovery,
        "heal_action": action,
        "target_pid": target_pid
    }

def calculate_health_score(d):
    """Compute a 0-100 PC Health Score based on real metrics and findings."""
    score = 100
    # CPU deduction
    cpu_pct = d["cpu"]["usage_percent"]
    if cpu_pct > 90:
        score -= 20
    elif cpu_pct > 75:
        score -= 10
        
    # RAM deduction
    ram_pct = d["ram"]["percent"]
    if ram_pct > 90:
        score -= 20
    elif ram_pct > 80:
        score -= 10
        
    # Disk space deduction
    for disk in d["disks"]:
        if disk["percent"] > 95:
            score -= 25
        elif disk["percent"] > 85:
            score -= 12
            
    # Uptime deduction
    if d["os"]["uptime_hours"] > 24 * 14:
        score -= 10
    elif d["os"]["uptime_hours"] > 24 * 7:
        score -= 5
        
    # Hung apps deduction
    if d.get("hung_apps"):
        score -= min(len(d["hung_apps"]) * 10, 20)
        
    # Defender status
    defend = d.get("defender", {})
    if defend.get("available") and not defend.get("realtime_enabled"):
        score -= 15
        
    # Suspicious processes
    if d.get("suspicious"):
        score -= min(len(d["suspicious"]) * 10, 25)
        
    return max(10, min(100, score))

def analyze(d):
    """Turn raw measurements into categorized, actionable findings."""
    f = []
    
    # 1. CPU
    if d["cpu"]["usage_percent"] > 85:
        top_name = d["top_cpu_processes"][0]["name"] if d.get("top_cpu_processes") else "active background task"
        f.append(_f(
            "high",
            f"High CPU usage ({d['cpu']['usage_percent']}%)",
            f"Intense CPU compute, possibly driven by {top_name}.",
            "Slowness, elevated system temperatures, fan noise, and sluggish response times.",
            "Inspect running apps; close heavy processes or let background jobs finish.",
            "Fully recoverable once intensive processes finish or are terminated."
        ))
        
    # 2. RAM
    if d["ram"]["percent"] > 85:
        f.append(_f(
            "high",
            f"High memory usage ({d['ram']['percent']}%)",
            "Too many memory-heavy applications or potential memory leak.",
            "Heavy paging to disk, stuttering, system lag, and app crashes.",
            "Close unused browser tabs and memory-hungry applications.",
            "Reversible immediately upon closing apps or restarting."
        ))
        
    # 3. Disks
    for k in d["disks"]:
        if k["percent"] > 90:
            f.append(_f(
                "high" if k["percent"] > 95 else "medium",
                f"Disk {k['mount']} critically low on space ({k['percent']}% used, {k['free_gb']} GB free)",
                "Accumulated temporary files, system caches, or large media.",
                "Windows updates cannot install, virtual memory paging slows down, disk fragmentation.",
                "Run Temp Cleaner or Disk Cleanup to clear cached files.",
                "Temporary cache deletion is safe. Manual file deletion is permanent.",
                action="clean_temp"
            ))
            
    # 4. Hung / Unresponsive Applications
    for hung in d.get("hung_apps", []):
        f.append(_f(
            "high",
            f"Unresponsive App: {hung['name']} (PID {hung['pid']})",
            hung["reason"],
            "Application is frozen and not accepting user input.",
            "Safely terminate the hung process using Self-Healing.",
            "Unsaved changes in the frozen app may be lost upon termination.",
            action="restart_unresponsive_app",
            target_pid=hung["pid"]
        ))
        
    # 5. Uptime
    if d["os"]["uptime_hours"] > 24 * 14:
        f.append(_f(
            "low",
            f"PC has been running continuously for {d['os']['uptime_hours']} hours ({round(d['os']['uptime_hours']/24, 1)} days)",
            "System has not rebooted in over 2 weeks.",
            "Accumulated kernel memory fragmentation and pending Windows update delays.",
            "Perform a clean system restart when convenient.",
            "Save open work before restarting."
        ))
        
    # 6. Startup Apps
    if len(d["startup_apps"]) > 10:
        f.append(_f(
            "low",
            f"{len(d['startup_apps'])} applications configured to auto-start at boot",
            "Programs added to Windows Startup registry run automatically on login.",
            "Slower boot times and higher idle background RAM consumption.",
            "Disable unnecessary startup applications in Task Manager > Startup.",
            "Fully reversible."
        ))
        
    # 7. Suspicious Processes
    for s in d.get("suspicious", []):
        f.append(_f(
            "medium",
            f"Suspicious indicator: {s['name']} (PID {s['pid']})",
            s["reason"],
            "Could be a legitimate installer or potentially unwanted background software.",
            "Verify file origin; perform a Windows Defender virus scan.",
            "SelfHeal IT is a health diagnostics tool, not an antivirus - use Windows Defender."
        ))
        
    # 8. Windows Defender Status
    defend = d.get("defender", {})
    if defend.get("available") and not defend.get("realtime_enabled"):
        f.append(_f(
            "high",
            "Windows Defender Real-Time Protection is disabled",
            "Defender real-time monitoring is currently switched off.",
            "Leaves PC vulnerable to malicious downloads and active malware execution.",
            "Enable Real-Time Protection in Windows Security Settings.",
            "Immediate protection restored once turned on."
        ))
        
    return f

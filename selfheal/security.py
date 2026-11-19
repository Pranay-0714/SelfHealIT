"""Security Subsystem for SelfHeal IT.
Monitors Windows Defender status, analyzes suspicious processes, audits open listening ports
and external network sockets, and allows triggering Defender scans upon user approval."""
import platform, subprocess, os, re, socket
import psutil

SUSPICIOUS_PATHS = [
    r"\temp\\", r"\appdata\local\temp", r"\tmp\\", r"\downloads\\", r"\users\public\\"
]

WELL_KNOWN_RISKY_PORTS = {
    21: "FTP (Plaintext credentials)",
    23: "Telnet (Unencrypted remote terminal)",
    25: "SMTP (Open mail relay risk)",
    445: "SMB / Active Directory (WannaCry / EternalBlue vector)",
    3389: "RDP (Remote Desktop Protocol exposed)",
    5900: "VNC (Remote access protocol)",
    8080: "HTTP Alternate (Potential web proxy or debug server)"
}

def _run_ps(cmd_str, timeout=10):
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd_str],
                           capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() or None
    except Exception:
        return None

def get_defender_status():
    """Detailed Windows Defender & Windows Security status."""
    if platform.system() != "Windows":
        return {
            "available": False,
            "status": "Unavailable",
            "message": "Windows Defender is only present on Microsoft Windows OS."
        }
        
    cmd = ("Get-MpComputerStatus | Select-Object -Property "
           "AntivirusEnabled, RealTimeProtectionEnabled, AntivirusSignatureAge, "
           "AntivirusSignatureVersion, QuickScanAge, AMServiceEnabled, AntispywareEnabled, "
           "BehaviorMonitorEnabled, IoavProtectionEnabled, NISSignatureVersion | ConvertTo-Json")
           
    raw = _run_ps(cmd, timeout=8)
    if not raw:
        return {
            "available": False,
            "status": "Unknown",
            "message": "Unable to query Windows Defender status via PowerShell."
        }
        
    try:
        import json
        d = json.loads(raw)
        if isinstance(d, dict):
            av_on = bool(d.get("AntivirusEnabled", False))
            rt_on = bool(d.get("RealTimeProtectionEnabled", False))
            svc_on = bool(d.get("AMServiceEnabled", False))
            
            sig_age = d.get("AntivirusSignatureAge")
            if isinstance(sig_age, int) and sig_age < 36500:
                sig_age_days = sig_age
            else:
                sig_age_days = None
                
            scan_age = d.get("QuickScanAge")
            if isinstance(scan_age, int) and scan_age < 36500:
                scan_age_days = scan_age
            else:
                scan_age_days = None
                
            status_summary = "Healthy" if (av_on and rt_on) else "Attention Needed"
            
            return {
                "available": True,
                "status": status_summary,
                "antivirus_enabled": av_on,
                "realtime_enabled": rt_on,
                "service_enabled": svc_on,
                "antispyware_enabled": bool(d.get("AntispywareEnabled", False)),
                "behavior_monitor": bool(d.get("BehaviorMonitorEnabled", False)),
                "ioav_protection": bool(d.get("IoavProtectionEnabled", False)),
                "signature_version": str(d.get("AntivirusSignatureVersion", "N/A")),
                "signature_age_days": sig_age_days,
                "quick_scan_age_days": scan_age_days
            }
    except Exception:
        pass
        
    return {"available": False, "status": "Error", "message": "Failed to parse Defender telemetry."}

def audit_suspicious_processes():
    """Scan running processes for security anomalies:
    1. Executing from temp/downloads/public paths
    2. Masquerading system binaries (e.g. svchost.exe not in System32)
    3. High foreign network connection counts."""
    suspicious = []
    win_dir = os.environ.get("WINDIR", r"C:\Windows").lower()
    system32_dir = os.path.join(win_dir, "system32").lower()
    
    SYSTEM_BINARIES = {
        "svchost.exe": system32_dir,
        "lsass.exe": system32_dir,
        "services.exe": system32_dir,
        "csrss.exe": system32_dir,
        "smss.exe": system32_dir,
        "winlogon.exe": system32_dir,
        "explorer.exe": win_dir
    }
    
    for p in psutil.process_iter(["pid", "name", "exe", "cmdline", "username"]):
        try:
            info = p.info
            p_name = (info["name"] or "").lower()
            exe = (info.get("exe") or "").lower()
            pid = info["pid"]
            
            if not exe:
                continue
                
            # 1. Check path
            for path_pattern in SUSPICIOUS_PATHS:
                if path_pattern in exe:
                    suspicious.append({
                        "pid": pid,
                        "name": info["name"],
                        "exe": exe,
                        "type": "temp_location",
                        "severity": "medium",
                        "description": f"Process executes from temp/untrusted directory: {exe}"
                    })
                    break
                    
            # 2. Check masquerading
            if p_name in SYSTEM_BINARIES:
                expected_dir = SYSTEM_BINARIES[p_name]
                actual_dir = os.path.dirname(exe)
                if expected_dir not in actual_dir:
                    suspicious.append({
                        "pid": pid,
                        "name": info["name"],
                        "exe": exe,
                        "type": "masquerading_system_binary",
                        "severity": "critical",
                        "description": f"Critical security alert: Process '{info['name']}' is running from '{actual_dir}' instead of expected '{expected_dir}'."
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
            
    return suspicious

def audit_network_ports():
    """Inspect all open listening ports and active foreign sockets mapped to PIDs."""
    listening_ports = []
    active_connections = []
    
    try:
        conns = psutil.net_connections(kind="inet")
    except Exception:
        return {"listening": [], "active": [], "error": "Administrative permissions required for full socket mapping."}
        
    proc_cache = {}
    
    for c in conns:
        pid = c.pid
        proc_name = "System / Unknown"
        if pid:
            if pid not in proc_cache:
                try:
                    proc_cache[pid] = psutil.Process(pid).name()
                except Exception:
                    proc_cache[pid] = "Terminated"
            proc_name = proc_cache[pid]
            
        l_ip, l_port = c.laddr.ip, c.laddr.port if c.laddr else ("0.0.0.0", 0)
        
        if c.status == "LISTEN":
            flag = WELL_KNOWN_RISKY_PORTS.get(l_port)
            listening_ports.append({
                "port": l_port,
                "ip": l_ip,
                "pid": pid,
                "process": proc_name,
                "is_risky": bool(flag),
                "risk_note": flag or ""
            })
        elif c.status == "ESTABLISHED" and c.raddr:
            r_ip, r_port = c.raddr.ip, c.raddr.port
            # Filter localhost connections
            if not r_ip.startswith("127.") and r_ip != "::1":
                active_connections.append({
                    "local": f"{l_ip}:{l_port}",
                    "remote": f"{r_ip}:{r_port}",
                    "remote_ip": r_ip,
                    "pid": pid,
                    "process": proc_name
                })
                
    # Sort listening ports numerically
    listening_ports.sort(key=lambda x: x["port"])
    return {
        "listening": listening_ports[:40],
        "active": active_connections[:40],
        "total_listening": len(listening_ports),
        "total_active": len(active_connections)
    }

def trigger_defender_scan(scan_type="QuickScan", confirmed=False):
    """Trigger a Windows Defender scan. Requires explicit confirmation."""
    if not confirmed:
        return {"ok": False, "error": "Explicit user confirmation is required to start a Windows Defender scan."}
    if platform.system() != "Windows":
        return {"ok": False, "error": "Windows Defender is only supported on Windows."}
        
    valid_types = {"QuickScan": 1, "FullScan": 2}
    if scan_type not in valid_types:
        return {"ok": False, "error": "Invalid scan type (allowed: QuickScan, FullScan)."}
        
    cmd = ["powershell", "-NoProfile", "-Command", f"Start-MpScan -ScanType {scan_type} -AsJob"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return {
            "ok": r.returncode == 0,
            "scan_type": scan_type,
            "message": f"Windows Defender {scan_type} successfully initiated in the background." if r.returncode == 0 else f"Failed to launch scan: {r.stderr.strip()}"
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "message": "Failed to invoke PowerShell Start-MpScan"}

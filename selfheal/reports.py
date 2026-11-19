"""JSON and pure-Python dependency-free PDF export for PC Health Reports.
Generates comprehensive diagnostic reports with system metrics, hardware breakdown,
categorized findings, security status, and transparency disclosures."""
import json

def to_json(scan):
    """Serialize scan data to cleanly indented JSON."""
    return json.dumps(scan, indent=2)

def report_lines(scan):
    """Format full scan telemetry into structured text lines for report generation."""
    L = [
        "=======================================================================",
        "                     SELFHEAL IT - PC HEALTH REPORT                    ",
        "                Comprehensive Windows System Diagnostics               ",
        "=======================================================================",
        f"Generated: {scan.get('timestamp', 'N/A')}",
        f"Health Score: {scan.get('health_score', 100)} / 100",
        "",
        "--- SYSTEM SPECIFICATIONS ---",
        f"Operating System : {scan['os']['system']} {scan['os']['release']} (Build {scan['os'].get('version', 'N/A')})",
        f"Architecture     : {scan['os'].get('architecture', 'x86_64')}",
        f"System Uptime    : {scan['os']['uptime_hours']} hours ({round(scan['os']['uptime_hours']/24, 1)} days)",
        f"Processor (CPU)  : {scan['cpu']['name']}",
        f"CPU Cores/Clock  : {scan['cpu']['physical_cores']} Physical / {scan['cpu']['logical_cores']} Logical @ {scan['cpu'].get('current_mhz') or scan['cpu'].get('max_mhz') or 'N/A'} MHz",
        f"Current CPU Load : {scan['cpu']['usage_percent']}%",
        f"System RAM       : {scan['ram']['total_gb']} GB total ({scan['ram']['percent']}% used, {scan['ram']['available_gb']} GB available)",
        f"Graphics (GPU)   : {scan['gpu']}",
        ""
    ]
    
    # Storage section
    L.append("--- STORAGE & DISK DRIVES ---")
    if scan.get("disks"):
        for d in scan["disks"]:
            L.append(f"Drive {d['mount']:<4} : {d['used_gb']} GB used of {d['total_gb']} GB ({d['percent']}% full) - {d['free_gb']} GB free")
    else:
        L.append("No disk storage drives detected.")
    L.append("")
    
    # Security & Defender section
    L.append("--- SECURITY AUDIT ---")
    defend = scan.get("defender", {})
    if defend.get("available"):
        rt = "Enabled" if defend.get("realtime_enabled") else "DISABLED / WARNING"
        av = "Enabled" if defend.get("antivirus_enabled") else "Disabled"
        L.append(f"Windows Defender Real-Time Protection : {rt}")
        L.append(f"Antivirus Engine Status                : {av}")
        L.append(f"Definitions Version                    : {defend.get('signature_version', 'Unknown')}")
    else:
        L.append("Windows Defender telemetry unavailable.")
        
    suspicious = scan.get("suspicious", [])
    if suspicious:
        L.append(f"Suspicious Indicators Flagged         : {len(suspicious)} process(es)")
        for s in suspicious[:3]:
            L.append(f"  * {s['name']} (PID {s['pid']}): {s['reason']}")
    else:
        L.append("Suspicious Process Heuristics         : None flagged (Clean)")
    L.append("")
    
    # Top Resource Users
    L.append("--- TOP RESOURCE-CONSUMING PROCESSES ---")
    top_p = scan.get("top_processes", [])
    if top_p:
        for p in top_p[:5]:
            L.append(f"PID {p['pid']:<6} | {p['name']:<24} | RAM: {p.get('mem_percent', 0)}% | CPU: {p.get('cpu_percent', 0)}%")
    else:
        L.append("No active process list collected.")
    L.append("")
    
    # Findings and Actionable Diagnostics
    L.append("--- DIAGNOSTIC FINDINGS & HEALING RECOMMENDATIONS ---")
    findings = scan.get("findings", [])
    if not findings:
        L.append("[STATUS: OPTIMAL] No hardware or software issues detected during scan.")
    else:
        for idx, f in enumerate(findings, 1):
            sev = f.get("severity", "info").upper()
            L.append(f"[{sev}] Issue #{idx}: {f.get('problem', 'Unknown Issue')}")
            L.append(f"  Root Cause  : {f.get('cause', 'N/A')}")
            L.append(f"  Consequence : {f.get('consequence', 'N/A')}")
            L.append(f"  Solution    : {f.get('solution', 'N/A')}")
            L.append(f"  Recovery    : {f.get('recovery', 'N/A')}")
            if f.get("heal_action"):
                L.append(f"  Self-Heal   : Safe action available: '{f.get('heal_action')}'")
            L.append("")
            
    # Legal / Transparency Disclaimers
    L.append("=======================================================================")
    L.append("DISCLOSURE: SelfHeal IT is a PC health diagnostics and recovery tool.   ")
    L.append("It does not replace antivirus software such as Windows Defender.       ")
    L.append("All self-healing actions require explicit user confirmation.           ")
    L.append("=======================================================================")
    
    return L

def to_pdf(scan):
    """Pure-Python dependency-free PDF 1.4 writer with multi-page support."""
    def esc(s):
        # Clean latin-1 escape for PDF strings
        clean = s.encode("latin-1", "replace").decode("latin-1")
        return clean.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        
    lines = report_lines(scan)
    lines_per_page = 48
    pages = [lines[i:i + lines_per_page] for i in range(0, len(lines), lines_per_page)]
    if not pages:
        pages = [["No data."]]
        
    # Objects array: 1 = Catalog, 2 = Pages, 3 = Font
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        None,  # Placeholder for Pages object
        "<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>"
    ]
    
    kids = []
    for pg in pages:
        txt = "BT /F1 9 Tf 36 805 Td 15 TL\n" + "\n".join(f"({esc(line[:100])}) '" for line in pg) + "\nET"
        txt_bytes = txt.encode("latin-1")
        content_obj_idx = len(objs) + 1
        objs.append(f"<< /Length {len(txt_bytes)} >>\nstream\n{txt}\nendstream")
        
        page_obj_idx = len(objs) + 1
        objs.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Contents {content_obj_idx} 0 R /Resources << /Font << /F1 3 0 R >> >> >>"
        )
        kids.append(f"{page_obj_idx} 0 R")
        
    # Set Pages object
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"
    
    out = b"%PDF-1.4\n"
    offsets = []
    
    for n, o in enumerate(objs, 1):
        offsets.append(len(out))
        if isinstance(o, str):
            out += f"{n} 0 obj\n{o}\nendobj\n".encode("latin-1")
        else:
            out += f"{n} 0 obj\n".encode("latin-1") + o + b"\nendobj\n"
            
    xref_offset = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode("latin-1")
    for o in offsets:
        out += f"{o:010d} 00000 n \n".encode("latin-1")
        
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("latin-1")
    return out

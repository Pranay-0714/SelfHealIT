"""Chatbot grounded in live scan data.
Supports multiple AI backends (Gemini, OpenAI, Anthropic) with an intelligent,
rule-based and heuristic fallback engine.
Includes dedicated Game/Software Compatibility analysis and Bottleneck Diagnosis."""
import os, re, json, urllib.request, urllib.parse
from selfheal import config

# Comprehensive database of System Requirements for Games and Professional Workstation Software
# Format: "title": {
#   "name": "Display Name",
#   "type": "game" | "software",
#   "min": {"ram_gb": X, "cores": Y, "vram_gb": Z, "storage_gb": S, "tier": "low"|"mid"|"high"},
#   "rec": {"ram_gb": X, "cores": Y, "vram_gb": Z, "storage_gb": S, "tier": "low"|"mid"|"high"},
#   "notes": "Specific requirement caveats"
# }
REQUIREMENTS_DB = {
    "minecraft": {
        "name": "Minecraft (Java Edition)",
        "type": "game",
        "min": {"ram_gb": 4, "cores": 2, "vram_gb": 0.5, "storage_gb": 4, "tier": "low"},
        "rec": {"ram_gb": 8, "cores": 4, "vram_gb": 2.0, "storage_gb": 10, "tier": "mid"},
        "notes": "Vanilla runs on low specs, but shaders or heavily modded packs need 8-16 GB RAM and dedicated GPU."
    },
    "valorant": {
        "name": "Valorant",
        "type": "game",
        "min": {"ram_gb": 4, "cores": 2, "vram_gb": 1.0, "storage_gb": 30, "tier": "low"},
        "rec": {"ram_gb": 8, "cores": 4, "vram_gb": 2.0, "storage_gb": 40, "tier": "mid"},
        "notes": "Requires Windows TPM 2.0 and Secure Boot for Vanguard anti-cheat on Windows 11."
    },
    "fortnite": {
        "name": "Fortnite",
        "type": "game",
        "min": {"ram_gb": 8, "cores": 4, "vram_gb": 2.0, "storage_gb": 35, "tier": "mid"},
        "rec": {"ram_gb": 16, "cores": 6, "vram_gb": 4.0, "storage_gb": 50, "tier": "mid"},
        "notes": "Performance Mode allows playable framerates on integrated graphics; DirectX 12 requires dedicated GPU."
    },
    "gta v": {
        "name": "Grand Theft Auto V",
        "type": "game",
        "min": {"ram_gb": 8, "cores": 4, "vram_gb": 1.0, "storage_gb": 110, "tier": "mid"},
        "rec": {"ram_gb": 16, "cores": 4, "vram_gb": 4.0, "storage_gb": 110, "tier": "mid"},
        "notes": "Requires significant disk space (110+ GB). High textures benefit greatly from 4+ GB VRAM."
    },
    "cyberpunk 2077": {
        "name": "Cyberpunk 2077",
        "type": "game",
        "min": {"ram_gb": 12, "cores": 6, "vram_gb": 6.0, "storage_gb": 70, "tier": "high"},
        "rec": {"ram_gb": 16, "cores": 8, "vram_gb": 8.0, "storage_gb": 70, "tier": "high"},
        "notes": "SSD is mandatory. Integrated graphics will not provide playable performance."
    },
    "elden ring": {
        "name": "Elden Ring",
        "type": "game",
        "min": {"ram_gb": 12, "cores": 4, "vram_gb": 3.0, "storage_gb": 60, "tier": "high"},
        "rec": {"ram_gb": 16, "cores": 6, "vram_gb": 6.0, "storage_gb": 60, "tier": "high"},
        "notes": "Demands strong single-core CPU speed and DirectX 12 Level 12_0 compatible GPU."
    },
    "counter-strike 2": {
        "name": "Counter-Strike 2 (CS2)",
        "type": "game",
        "min": {"ram_gb": 8, "cores": 4, "vram_gb": 2.0, "storage_gb": 85, "tier": "mid"},
        "rec": {"ram_gb": 16, "cores": 6, "vram_gb": 4.0, "storage_gb": 85, "tier": "mid"},
        "notes": "Source 2 engine is much more GPU intensive than CS:GO; requires Vulkan or DX11 support."
    },
    "cs2": {
        "name": "Counter-Strike 2 (CS2)",
        "type": "game",
        "min": {"ram_gb": 8, "cores": 4, "vram_gb": 2.0, "storage_gb": 85, "tier": "mid"},
        "rec": {"ram_gb": 16, "cores": 6, "vram_gb": 4.0, "storage_gb": 85, "tier": "mid"},
        "notes": "Source 2 engine requires dedicated GPU for smooth 60+ FPS competitive gameplay."
    },
    "red dead redemption 2": {
        "name": "Red Dead Redemption 2",
        "type": "game",
        "min": {"ram_gb": 8, "cores": 4, "vram_gb": 2.0, "storage_gb": 150, "tier": "high"},
        "rec": {"ram_gb": 12, "cores": 6, "vram_gb": 6.0, "storage_gb": 150, "tier": "high"},
        "notes": "Huge 150 GB storage footprint. High graphic presets require 6+ GB VRAM."
    },
    "apex legends": {
        "name": "Apex Legends",
        "type": "game",
        "min": {"ram_gb": 6, "cores": 4, "vram_gb": 1.0, "storage_gb": 65, "tier": "mid"},
        "rec": {"ram_gb": 8, "cores": 4, "vram_gb": 4.0, "storage_gb": 65, "tier": "mid"},
        "notes": "Adaptive resolution scaling helps on entry-level systems."
    },
    "blender": {
        "name": "Blender 3D",
        "type": "software",
        "min": {"ram_gb": 8, "cores": 4, "vram_gb": 2.0, "storage_gb": 2, "tier": "mid"},
        "rec": {"ram_gb": 32, "cores": 8, "vram_gb": 8.0, "storage_gb": 20, "tier": "high"},
        "notes": "Cycles rendering benefits heavily from NVIDIA CUDA/OptiX or AMD HIP GPU acceleration."
    },
    "adobe premiere pro": {
        "name": "Adobe Premiere Pro",
        "type": "software",
        "min": {"ram_gb": 8, "cores": 4, "vram_gb": 2.0, "storage_gb": 10, "tier": "mid"},
        "rec": {"ram_gb": 32, "cores": 8, "vram_gb": 6.0, "storage_gb": 50, "tier": "high"},
        "notes": "4K video editing requires minimum 32 GB system RAM and fast NVMe storage cache."
    },
    "premiere": {
        "name": "Adobe Premiere Pro",
        "type": "software",
        "min": {"ram_gb": 8, "cores": 4, "vram_gb": 2.0, "storage_gb": 10, "tier": "mid"},
        "rec": {"ram_gb": 32, "cores": 8, "vram_gb": 6.0, "storage_gb": 50, "tier": "high"},
        "notes": "Multi-cam and 4K editing recommend 32GB RAM."
    },
    "photoshop": {
        "name": "Adobe Photoshop",
        "type": "software",
        "min": {"ram_gb": 8, "cores": 4, "vram_gb": 1.5, "storage_gb": 10, "tier": "mid"},
        "rec": {"ram_gb": 16, "cores": 6, "vram_gb": 4.0, "storage_gb": 20, "tier": "mid"},
        "notes": "Scratch disks require 20+ GB free space on primary drive."
    },
    "android studio": {
        "name": "Android Studio",
        "type": "software",
        "min": {"ram_gb": 8, "cores": 4, "vram_gb": 0, "storage_gb": 15, "tier": "mid"},
        "rec": {"ram_gb": 16, "cores": 8, "vram_gb": 2.0, "storage_gb": 30, "tier": "high"},
        "notes": "Running Android Virtual Device (AVD) emulator alongside Gradle build demands 16 GB RAM."
    },
    "docker": {
        "name": "Docker Desktop",
        "type": "software",
        "min": {"ram_gb": 8, "cores": 4, "vram_gb": 0, "storage_gb": 10, "tier": "mid"},
        "rec": {"ram_gb": 16, "cores": 6, "vram_gb": 0, "storage_gb": 30, "tier": "mid"},
        "notes": "Requires WSL 2 (Windows Subsystem for Linux) and CPU virtualization (VT-x/AMD-V) enabled in BIOS."
    },
    "vs code": {
        "name": "Visual Studio Code",
        "type": "software",
        "min": {"ram_gb": 2, "cores": 2, "vram_gb": 0, "storage_gb": 1, "tier": "low"},
        "rec": {"ram_gb": 8, "cores": 4, "vram_gb": 0, "storage_gb": 5, "tier": "low"},
        "notes": "Very lightweight; heavy extensions or large TypeScript workspaces consume more memory."
    },
    "visual studio code": {
        "name": "Visual Studio Code",
        "type": "software",
        "min": {"ram_gb": 2, "cores": 2, "vram_gb": 0, "storage_gb": 1, "tier": "low"},
        "rec": {"ram_gb": 8, "cores": 4, "vram_gb": 0, "storage_gb": 5, "tier": "low"},
        "notes": "Very lightweight baseline."
    },
    "pycharm": {
        "name": "PyCharm IDE",
        "type": "software",
        "min": {"ram_gb": 4, "cores": 2, "vram_gb": 0, "storage_gb": 5, "tier": "low"},
        "rec": {"ram_gb": 8, "cores": 4, "vram_gb": 0, "storage_gb": 10, "tier": "mid"},
        "notes": "Indexing large Python virtual environments is CPU and memory intensive."
    },
    "unity": {
        "name": "Unity Editor",
        "type": "software",
        "min": {"ram_gb": 8, "cores": 4, "vram_gb": 2.0, "storage_gb": 15, "tier": "mid"},
        "rec": {"ram_gb": 16, "cores": 8, "vram_gb": 4.0, "storage_gb": 40, "tier": "high"},
        "notes": "Complex 3D scenes benefit from dedicated GPU and multi-core compilation."
    },
    "unreal engine": {
        "name": "Unreal Engine 5",
        "type": "software",
        "min": {"ram_gb": 16, "cores": 6, "vram_gb": 6.0, "storage_gb": 100, "tier": "high"},
        "rec": {"ram_gb": 32, "cores": 8, "vram_gb": 8.0, "storage_gb": 150, "tier": "high"},
        "notes": "Lumen and Nanite require modern DirectX 12 GPU and massive storage."
    },
    "chrome": {
        "name": "Google Chrome",
        "type": "software",
        "min": {"ram_gb": 4, "cores": 2, "vram_gb": 0, "storage_gb": 1, "tier": "low"},
        "rec": {"ram_gb": 8, "cores": 4, "vram_gb": 0, "storage_gb": 5, "tier": "low"},
        "notes": "RAM usage scales with active tabs; 50+ tabs can easily exceed 4-6 GB RAM."
    },
    "python": {
        "name": "Python Development",
        "type": "software",
        "min": {"ram_gb": 2, "cores": 1, "vram_gb": 0, "storage_gb": 1, "tier": "low"},
        "rec": {"ram_gb": 8, "cores": 4, "vram_gb": 0, "storage_gb": 5, "tier": "low"},
        "notes": "Standard scripting is very lightweight; data science (Pandas/ML) requires 8-16+ GB RAM."
    }
}

# Compatibility helper: legacy alias dictionary preserved for backwards-compatible test calls
REQS = {k: (v["min"]["ram_gb"], v["min"]["cores"]) for k, v in REQUIREMENTS_DB.items()}

def check_compatibility(target_name, scan):
    """Detailed hardware vs software compatibility analysis."""
    if not scan:
        return {"ok": False, "error": "Run a scan first to collect hardware specifications."}
    
    key = target_name.strip().lower()
    matched_entry = None
    for k, v in REQUIREMENTS_DB.items():
        if k in key or key in k:
            matched_entry = v
            break
            
    if not matched_entry:
        return {
            "ok": False,
            "title": target_name,
            "found": False,
            "message": f"I don't have verified specifications for '{target_name}' in my local database, so I won't guess. Check the official publisher page and compare against your hardware:",
            "specs": {
                "ram_gb": scan["ram"]["total_gb"],
                "logical_cores": scan["cpu"]["logical_cores"],
                "physical_cores": scan["cpu"]["physical_cores"],
                "gpu": scan["gpu"]
            }
        }
        
    user_ram = scan["ram"]["total_gb"]
    user_cores = scan["cpu"]["logical_cores"] or 2
    user_gpu_str = (scan.get("gpu") or "").lower()
    gpus_list = scan.get("gpus", [])
    user_vram = max([g.get("memory_gb", 0) for g in gpus_list] or [0])
    is_integrated = any(x in user_gpu_str for x in ("intel", "uhd", "hd graphics", "vega 3", "basic display"))
    
    min_req = matched_entry["min"]
    rec_req = matched_entry["rec"]
    
    ram_ok_min = user_ram >= min_req["ram_gb"]
    ram_ok_rec = user_ram >= rec_req["ram_gb"]
    cores_ok_min = user_cores >= min_req["cores"]
    cores_ok_rec = user_cores >= rec_req["cores"]
    
    gpu_tier = min_req.get("tier", "low")
    gpu_min_ok = True
    gpu_rec_ok = True
    gpu_note = "Integrated GPU meets low-tier requirements."
    
    if gpu_tier in ("mid", "high"):
        if is_integrated and min_req.get("vram_gb", 0) >= 2.0:
            gpu_min_ok = False
            gpu_rec_ok = False
            gpu_note = f"Warning: Game/App requires dedicated GPU with {min_req['vram_gb']}GB VRAM. Your system has an integrated GPU ({scan['gpu']}) which may cause stuttering or fail to launch."
        elif user_vram > 0 and user_vram < min_req.get("vram_gb", 0):
            gpu_min_ok = False
            gpu_note = f"Your GPU has {user_vram} GB VRAM, but minimum required is {min_req['vram_gb']} GB."
        else:
            gpu_note = f"GPU: {scan['gpu']}."
            
    meets_recommended = ram_ok_rec and cores_ok_rec and gpu_rec_ok
    meets_minimum = ram_ok_min and cores_ok_min and gpu_min_ok
    
    if meets_recommended:
        verdict = "Exceeds Recommended"
        summary = f"Your PC comfortably meets the recommended requirements for {matched_entry['name']}."
    elif meets_minimum:
        verdict = "Meets Minimum"
        summary = f"Your PC meets the minimum specifications for {matched_entry['name']}. You may need medium/low graphics settings for optimal performance."
    else:
        verdict = "Below Minimum"
        reasons = []
        if not ram_ok_min:
            reasons.append(f"RAM ({user_ram}GB vs {min_req['ram_gb']}GB needed)")
        if not cores_ok_min:
            reasons.append(f"CPU cores ({user_cores} vs {min_req['cores']} needed)")
        if not gpu_min_ok:
            reasons.append("GPU graphics capability")
        summary = f"Your PC is BELOW minimum requirements for {matched_entry['name']}: shortfall in {', '.join(reasons)}."

    return {
        "ok": True,
        "found": True,
        "title": matched_entry["name"],
        "type": matched_entry["type"],
        "verdict": verdict,
        "summary": summary,
        "details": {
            "ram": {"user": f"{user_ram} GB", "min": f"{min_req['ram_gb']} GB", "rec": f"{rec_req['ram_gb']} GB", "pass": ram_ok_min},
            "cpu_cores": {"user": f"{user_cores} threads", "min": f"{min_req['cores']} threads", "rec": f"{rec_req['cores']} threads", "pass": cores_ok_min},
            "gpu": {"user": scan["gpu"], "note": gpu_note, "pass": gpu_min_ok},
            "notes": matched_entry.get("notes", "")
        }
    }

def analyze_bottlenecks(scan):
    """Analyze real scan telemetry to diagnose primary hardware and performance bottlenecks."""
    if not scan:
        return "No scan data available. Run a health scan first."
    
    cpu = scan["cpu"]
    ram = scan["ram"]
    disks = scan["disks"]
    gpu = scan["gpu"]
    
    bottlenecks = []
    
    # 1. RAM Bottleneck
    if ram["total_gb"] <= 4:
        bottlenecks.append({
            "component": "RAM (Capacity)",
            "severity": "High",
            "desc": f"Total RAM is only {ram['total_gb']} GB. Modern Windows 10/11 and web browsers easily saturate 4 GB, causing heavy paging to disk."
        })
    elif ram["percent"] > 85:
        bottlenecks.append({
            "component": "RAM (Utilization)",
            "severity": "Medium",
            "desc": f"Memory is currently {ram['percent']}% full ({ram['available_gb']} GB available of {ram['total_gb']} GB). Active programs are competing for memory."
        })
        
    # 2. CPU Bottleneck
    physical_cores = cpu.get("physical_cores") or 2
    if physical_cores <= 2:
        bottlenecks.append({
            "component": "CPU (Core Count)",
            "severity": "Medium",
            "desc": f"CPU has only {physical_cores} physical cores ({cpu['logical_cores']} threads). Multitasking or background system scans will cause UI micro-stutters."
        })
    if cpu["usage_percent"] > 85:
        bottlenecks.append({
            "component": "CPU (Active Load)",
            "severity": "High",
            "desc": f"CPU utilization is currently peaked at {cpu['usage_percent']}%. The processor is saturated by active computations."
        })
        
    # 3. GPU Bottleneck
    gpu_lower = gpu.lower()
    if any(x in gpu_lower for x in ("intel hd", "intel uhd", "intel(r) hd", "basic display")):
        bottlenecks.append({
            "component": "GPU (Integrated Graphics)",
            "severity": "Medium",
            "desc": f"System relies on integrated {gpu}. Lacks dedicated high-speed VRAM for 3D games, video rendering, or CUDA acceleration."
        })
        
    # 4. Storage Bottleneck
    for d in disks:
        if d["percent"] > 90:
            bottlenecks.append({
                "component": f"Storage ({d['mount']})",
                "severity": "High",
                "desc": f"Drive {d['mount']} is {d['percent']}% full with only {d['free_gb']} GB free. Solid-state drives suffer degraded write performance when above 85-90% capacity."
            })
            
    if not bottlenecks:
        return "Bottleneck Analysis: System components appear well-balanced for daily productivity tasks. No acute hardware or utilization bottlenecks detected under current load."
        
    res = "Bottleneck Diagnosis:\n"
    for b in bottlenecks:
        res += f"• [{b['severity']}] {b['component']}: {b['desc']}\n"
    return res.strip()

def rule_based(question, scan):
    """Accurate, zero-hallucination rule-based intelligence engine."""
    q = question.lower().strip()
    if scan is None:
        return "No scan data yet. Run a scan first so I can answer from your real system data."
    
    # 1. Compatibility queries
    compat_match = re.search(r"(?:can (?:i|my pc|we) run|play|compatibility for|requirements for)\s+([a-zA-Z0-9\s\.\-]+)", q)
    if compat_match:
        target = compat_match.group(1).strip()
        comp = check_compatibility(target, scan)
        if comp.get("found"):
            det = comp["details"]
            return (f"Compatibility Verdict for {comp['title']}: {comp['verdict']}.\n"
                    f"{comp['summary']}\n"
                    f"• RAM: {det['ram']['user']} (Min: {det['ram']['min']}, Rec: {det['ram']['rec']})\n"
                    f"• CPU: {det['cpu_cores']['user']} (Min: {det['cpu_cores']['min']}, Rec: {det['cpu_cores']['rec']})\n"
                    f"• GPU: {det['gpu']['note']}\n"
                    f"• Note: {det['notes']}")
        else:
            return comp.get("message", "Title not in database.") + f" ({scan['ram']['total_gb']} GB RAM, {scan['cpu']['logical_cores']} cores, GPU {scan['gpu']})."
            
    # Direct game name match fallback (preserves backward compatibility with original check)
    for name, (ram, cores) in REQS.items():
        if name in q:
            r, c = scan["ram"]["total_gb"], scan["cpu"]["logical_cores"] or 0
            ok = r >= ram and c >= cores
            return (f"For {name} (approx. minimum {ram} GB RAM, {cores} cores): you have {r} GB RAM and {c} logical cores -> "
                    f"{'meets the minimum' if ok else 'BELOW the minimum'}. GPU: {scan['gpu']} - I can't verify GPU "
                    f"requirements from my local list; check the official page.")
                    
    # Generic requirements query
    if re.search(r"can (i|my).*(run|play)|requirements", q):
        return ("I don't have requirements for that title in my local list, so I won't guess. Check the official page and compare with: "
                f"{scan['ram']['total_gb']} GB RAM, {scan['cpu']['logical_cores']} cores, GPU {scan['gpu']}.")
                
    # 2. Bottlenecks
    if "bottleneck" in q or "choke" in q or "limiting factor" in q or "upgrade" in q:
        return analyze_bottlenecks(scan)
        
    # 3. RAM / Memory
    if "ram" in q or "memory" in q:
        r = scan["ram"]
        return f"RAM: {r['total_gb']} GB total, {r['available_gb']} GB available ({r['percent']}% used, {r.get('used_gb', 0)} GB active). Swap/Pagefile: {r.get('swap_percent', 0)}% used."
        
    # 4. CPU / Slowness / Fans
    if "cpu" in q or "processor" in q or "fan" in q or "heat" in q or "slow" in q or "lag" in q:
        c = scan["cpu"]
        top_procs = scan.get("top_cpu_processes") or scan.get("top_processes", [])
        top_str = ", ".join(f"{p['name']} ({p.get('cpu_percent', p.get('mem_percent'))}%)" for p in top_procs[:3])
        return (f"CPU: {c['name']} with {c['physical_cores']} physical cores / {c['logical_cores']} threads.\n"
                f"Current total CPU utilization is {c['usage_percent']}%. Clock: {c.get('current_mhz') or c.get('max_mhz') or 'N/A'} MHz.\n"
                f"Top resource consumers: {top_str if top_str else 'none active'}.")
                
    # 5. Storage / Disk Space
    if "disk" in q or "storage" in q or "space" in q or "drive" in q or "ssd" in q or "hdd" in q:
        disks_info = "; ".join(f"{d['mount']} {d['free_gb']} GB free of {d['total_gb']} GB ({d['percent']}% used)" for d in scan["disks"])
        return f"Disk Partitions: {disks_info or 'No disk data.'}"
        
    # 6. GPU
    if "gpu" in q or "graphics" in q or "vram" in q or "video card" in q:
        return f"GPU: {scan['gpu']}"
        
    # 7. Wi-Fi / Network
    if "wifi" in q or "network" in q or "internet" in q or "ping" in q or "connection" in q:
        wifi = scan.get("wifi", {})
        net = scan.get("network", {})
        ssid = wifi.get("SSID", "Not connected via Wi-Fi")
        sig = wifi.get("Signal", "N/A")
        return f"Network Status:\n• Wi-Fi SSID: {ssid} (Signal: {sig})\n• Active Network Connections: {net.get('total', 0)} ({net.get('established', 0)} established, {net.get('listening', 0)} listening)."
        
    # 8. Security / Malware / Defender
    if "virus" in q or "malware" in q or "suspicious" in q or "safe" in q or "defender" in q or "security" in q:
        s = scan.get("suspicious", [])
        defend = scan.get("defender", {})
        head = (f"{len(s)} suspicious indicator(s) flagged: " + ", ".join(x["name"] for x in s)) if s else "No suspicious processes flagged by local heuristics."
        rt = "Real-time protection is ACTIVE" if defend.get("realtime_enabled") else "Real-time protection is INACTIVE / DISABLED"
        return f"{head}\n• Windows Defender: {rt}. Note: SelfHeal IT is a health diagnostics tool, not an antivirus; use Windows Defender for malware removal."
        
    # 9. Hung apps
    if "hung" in q or "unresponsive" in q or "frozen" in q:
        h = scan.get("hung_apps", [])
        if h:
            return f"Detected {len(h)} unresponsive window(s): " + ", ".join(f"{x['name']} (PID {x['pid']})" for x in h) + ". You can terminate them safely in the Self-Healing tab."
        return "No unresponsive or frozen application windows detected at this time."
        
    # 10. Overall Health & Findings
    if "health" in q or "score" in q or "problem" in q or "issue" in q or "diagnos" in q or "finding" in q:
        f = scan.get("findings", [])
        score = scan.get("health_score", 100)
        if f:
            lines = [f"Overall PC Health Score: {score}/100. Issues identified:"]
            for x in f:
                lines.append(f"• [{x['severity'].upper()}] {x['problem']}: {x['solution']}")
            return "\n".join(lines)
        return f"Overall PC Health Score: {score}/100. The scan found no active system problems."
        
    # Default helpful prompt
    f = scan.get("findings", [])
    if f:
        return f"Current System Findings ({len(f)}):\n" + "\n".join(f"• [{x['severity'].upper()}] {x['problem']}: {x['solution']}" for x in f[:4])
    return "The scan found no problems. You can ask about RAM, CPU, disk space, GPU, Wi-Fi, security status, bottleneck analysis, or ask 'Can I run [Game Name]'."

def ask_gemini(question, scan, api_key):
    """Query Google Gemini API using native REST endpoint."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    system_instruction = (
        "You are SelfHeal IT Assistant, an expert Windows diagnostics and IT support assistant. "
        "Answer questions accurately, grounding answers ONLY in the real scan JSON data provided. "
        "Never invent specs, never recommend dangerous terminal commands like format or deletion of Windows system files, "
        "and clearly disclose limitations when appropriate."
    )
    prompt = f"SCAN DATA:\n{json.dumps(scan)[:10000]}\n\nUSER QUESTION: {question}"
    
    payload = {
        "contents": [{"parts": [{"text": f"{system_instruction}\n\n{prompt}"}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 600}
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        candidates = res.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts and "text" in parts[0]:
                return {"answer": parts[0]["text"], "source": "gemini"}
    raise ValueError("Empty response from Gemini API")

def ask_openai(question, scan, api_key):
    """Query OpenAI API using REST endpoint."""
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": os.environ.get("SELFHEAL_OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {
                "role": "system",
                "content": "You are SelfHeal IT Assistant. Answer only based on the real Windows PC scan data provided. If data is missing, state it honestly. Never output arbitrary dangerous terminal commands."
            },
            {
                "role": "user",
                "content": f"SCAN DATA:\n{json.dumps(scan)[:10000]}\n\nQUESTION: {question}"
            }
        ],
        "temperature": 0.2,
        "max_tokens": 600
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        ans = res["choices"][0]["message"]["content"]
        return {"answer": ans, "source": "openai"}

def ask_anthropic(question, scan, api_key):
    """Query Anthropic Claude API."""
    body = {
        "model": os.environ.get("SELFHEAL_MODEL", "claude-sonnet-4-5"),
        "max_tokens": 600,
        "system": "You are SelfHeal IT's assistant. Answer ONLY from the scan JSON provided. "
                  "If information is missing, say so. Never invent specs or requirements, never output shell commands, "
                  "never promise recovery of unsaved work or OS crashes.",
        "messages": [{"role": "user", "content": f"SCAN:\n{json.dumps(scan)[:12000]}\n\nQUESTION: {question}"}]
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        json.dumps(body).encode(),
        {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return {"answer": json.load(r)["content"][0]["text"], "source": "llm"}

def ask(question, scan):
    """Unified entry point for AI queries."""
    if not question or not str(question).strip():
        return {"answer": "Please ask a question regarding your PC health or system specs.", "source": "system"}
        
    cfg = config.load_config()
    gemini_key = cfg.get("gemini_api_key")
    openai_key = cfg.get("openai_api_key")
    anthropic_key = cfg.get("anthropic_api_key")
    
    # Priority: Gemini -> OpenAI -> Anthropic -> Local Rule-Based
    if gemini_key and scan is not None:
        try:
            return ask_gemini(question, scan, gemini_key)
        except Exception:
            pass
            
    if openai_key and scan is not None:
        try:
            return ask_openai(question, scan, openai_key)
        except Exception:
            pass
            
    if anthropic_key and scan is not None:
        try:
            return ask_anthropic(question, scan, anthropic_key)
        except Exception:
            pass
            
    return {"answer": rule_based(question, scan), "source": "rule-based"}

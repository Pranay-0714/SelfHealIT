"""SelfHeal IT - Standalone Multi-PC Remote Agent.
Runs on secondary computers to monitor health and transmit telemetry
to the central SelfHeal IT management server using secure Bearer authentication."""
import sys, time, json, platform, socket, os, urllib.request, urllib.error
import psutil

# Configuration (Edit these or pass via command line arguments)
DEFAULT_SERVER_URL = "http://127.0.0.1:5000/api/agent/report"
DEFAULT_SECRET_KEY = "selfheal-agent-default-secret-token-key"
REPORT_INTERVAL_SEC = 10

def get_ip_address():
    """Retrieve local primary IPv4 address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def collect_telemetry():
    """Gather real-time PC health metrics."""
    cpu_pct = psutil.cpu_percent(interval=1.0)
    vm = psutil.virtual_memory()
    
    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            u = psutil.disk_usage(part.mountpoint)
            disks.append({
                "mount": part.mountpoint,
                "total_gb": round(u.total / (1024**3), 1),
                "free_gb": round(u.free / (1024**3), 1),
                "percent": u.percent
            })
        except Exception:
            pass
            
    findings = []
    if cpu_pct > 85:
        findings.append({"severity": "high", "problem": f"High CPU usage ({cpu_pct}%)"})
    if vm.percent > 85:
        findings.append({"severity": "high", "problem": f"High RAM usage ({vm.percent}%)"})
    for d in disks:
        if d["percent"] > 90:
            findings.append({"severity": "medium", "problem": f"Disk {d['mount']} almost full ({d['percent']}%)"})
            
    score = 100
    if cpu_pct > 85: score -= 20
    if vm.percent > 85: score -= 20
    for d in disks:
        if d["percent"] > 90: score -= 15
    score = max(20, min(100, score))
    
    return {
        "hostname": platform.node(),
        "ip": get_ip_address(),
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version()
        },
        "cpu_percent": cpu_pct,
        "ram_percent": vm.percent,
        "ram_total_gb": round(vm.total / (1024**3), 1),
        "disks": disks,
        "findings": findings,
        "health_score": score,
        "hung_apps": []
    }

def send_report(server_url, secret_key, data):
    """Transmit telemetry payload to central server."""
    payload_bytes = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        server_url,
        data=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {secret_key}"
        }
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    server_url = os.environ.get("SELFHEAL_SERVER", DEFAULT_SERVER_URL)
    secret_key = os.environ.get("SELFHEAL_SECRET", DEFAULT_SECRET_KEY)
    
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    if len(sys.argv) > 2:
        secret_key = sys.argv[2]
        
    print(f"[*] SelfHeal IT Remote Agent starting on: {platform.node()}")
    print(f"[*] Reporting to: {server_url}")
    print("[*] Press Ctrl+C to terminate agent.")
    
    consecutive_errors = 0
    while True:
        try:
            telemetry = collect_telemetry()
            resp = send_report(server_url, secret_key, telemetry)
            if consecutive_errors > 0:
                print(f"[+] Reconnected to SelfHeal IT server! Response: {resp.get('message', 'OK')}")
                consecutive_errors = 0
            else:
                print(f"[+] Telemetry reported: CPU {telemetry['cpu_percent']}% | RAM {telemetry['ram_percent']}% | Score {telemetry['health_score']}/100")
        except urllib.error.HTTPError as e:
            consecutive_errors += 1
            if e.code == 401:
                print(f"[-] Authentication failed (401 Unauthorized). Verify secret key matches server.")
            else:
                print(f"[-] HTTP error {e.code}: {e.reason}")
        except Exception as e:
            consecutive_errors += 1
            print(f"[-] Server unreachable: {e}. Retrying in {REPORT_INTERVAL_SEC}s...")
            
        time.sleep(REPORT_INTERVAL_SEC)

if __name__ == "__main__":
    main()

"""Multi-PC Fleet Management.
Aggregates health reports from distributed SelfHeal IT agents running on other PCs.
Enforces secure bearer token authentication and stores fleet telemetry."""
import os, json, time, datetime
from selfheal import config

FLEET_FILE = os.path.join(os.path.dirname(__file__), "..", "reports", "fleet.json")

def load_fleet():
    """Load persistent fleet state."""
    if os.path.exists(FLEET_FILE):
        try:
            with open(FLEET_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_fleet(fleet):
    """Save persistent fleet state."""
    try:
        os.makedirs(os.path.dirname(FLEET_FILE), exist_ok=True)
        with open(FLEET_FILE, "w", encoding="utf-8") as f:
            json.dump(fleet, f, indent=2)
    except Exception:
        pass

def authenticate_agent(auth_header):
    """Validate Bearer token against configured agent secret key."""
    if not auth_header:
        return False
    parts = auth_header.strip().split(" ")
    token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else auth_header.strip()
    
    cfg = config.load_config()
    secret = cfg.get("agent_secret_key", "")
    return bool(secret and token == secret)

def record_heartbeat(data, remote_ip="127.0.0.1"):
    """Ingest a health report from an authorized remote PC agent."""
    hostname = data.get("hostname") or data.get("name") or "Unknown-PC"
    now_ts = time.time()
    now_iso = datetime.datetime.now().isoformat(timespec="seconds")
    
    fleet = load_fleet()
    
    fleet[hostname] = {
        "hostname": hostname,
        "remote_ip": remote_ip,
        "os": data.get("os", {}),
        "cpu_percent": data.get("cpu_percent", 0),
        "ram_percent": data.get("ram_percent", 0),
        "ram_total_gb": data.get("ram_total_gb", 0),
        "disks": data.get("disks", []),
        "health_score": data.get("health_score", 100),
        "findings_count": len(data.get("findings", [])),
        "findings": data.get("findings", [])[:5],
        "hung_apps_count": len(data.get("hung_apps", [])),
        "last_seen_ts": now_ts,
        "last_seen_iso": now_iso,
        "status": "Online"
    }
    
    save_fleet(fleet)
    return fleet[hostname]

def get_fleet_summary():
    """Return all enrolled machines in the fleet with real-time Online/Offline status."""
    fleet = load_fleet()
    now = time.time()
    result = []
    
    for host, node in fleet.items():
        last_seen = node.get("last_seen_ts", 0)
        # Marked offline if no heartbeat within 45 seconds
        is_online = (now - last_seen) < 45
        node["status"] = "Online" if is_online else "Offline"
        node["seconds_ago"] = round(now - last_seen)
        result.append(node)
        
    result.sort(key=lambda x: (x["status"] != "Online", x["hostname"]))
    return result

def remove_agent(hostname):
    """Remove a decommissioned machine from the fleet."""
    fleet = load_fleet()
    if hostname in fleet:
        del fleet[hostname]
        save_fleet(fleet)
        return True
    return False

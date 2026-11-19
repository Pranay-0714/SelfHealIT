"""Live System Telemetry & Process Monitoring.
Collects real-time CPU, RAM, Network I/O metrics and detects unresponsive Windows applications."""
import time, collections, threading, platform, ctypes
import psutil
from selfheal import config

# Rolling buffer of historical performance samples (up to 60 samples = 2 mins at 2s interval)
MAX_SAMPLES = 60
_history_lock = threading.Lock()
_cpu_history = collections.deque(maxlen=MAX_SAMPLES)
_ram_history = collections.deque(maxlen=MAX_SAMPLES)
_net_in_history = collections.deque(maxlen=MAX_SAMPLES)
_net_out_history = collections.deque(maxlen=MAX_SAMPLES)
_timestamps = collections.deque(maxlen=MAX_SAMPLES)

_last_net = None
_last_time = None
_monitor_thread = None
_stop_event = threading.Event()

def get_hung_windows():
    """Detect non-responsive application windows in real time via user32.IsHungAppWindow."""
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
                    mem = round(p.memory_info().rss / (1024**2), 1)
                except Exception:
                    p_name = "Unknown"
                    mem = 0.0
                    
                if not any(h["pid"] == p_id for h in hung):
                    hung.append({
                        "pid": p_id,
                        "name": p_name,
                        "title": title,
                        "mem_mb": mem,
                        "reason": "Application window is not responding to Windows messages"
                    })
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    except Exception:
        pass
    return hung

def sample_metrics():
    """Collect one instantaneous sample of CPU, RAM, Network speeds, and hung apps."""
    global _last_net, _last_time
    now = time.time()
    iso_time = time.strftime("%H:%M:%S", time.localtime(now))
    
    cpu_pct = psutil.cpu_percent(None)
    vm = psutil.virtual_memory()
    ram_pct = vm.percent
    
    # Network I/O throughput
    net_in_kb = 0.0
    net_out_kb = 0.0
    try:
        curr_net = psutil.net_io_counters()
        if _last_net and _last_time:
            dt = max(0.1, now - _last_time)
            net_in_kb = round((curr_net.bytes_recv - _last_net.bytes_recv) / 1024.0 / dt, 1)
            net_out_kb = round((curr_net.bytes_sent - _last_net.bytes_sent) / 1024.0 / dt, 1)
        _last_net = curr_net
        _last_time = now
    except Exception:
        pass
        
    hung = get_hung_windows()
    
    with _history_lock:
        _timestamps.append(iso_time)
        _cpu_history.append(cpu_pct)
        _ram_history.append(ram_pct)
        _net_in_history.append(max(0.0, net_in_kb))
        _net_out_history.append(max(0.0, net_out_kb))
        
    cfg = config.load_config()
    cpu_thresh = cfg.get("cpu_alert_threshold", 85)
    ram_thresh = cfg.get("ram_alert_threshold", 85)
    
    alerts = []
    if cpu_pct > cpu_thresh:
        alerts.append({"type": "cpu", "level": "warning", "message": f"Elevated CPU usage: {cpu_pct}% (threshold {cpu_thresh}%)"})
    if ram_pct > ram_thresh:
        alerts.append({"type": "ram", "level": "warning", "message": f"Elevated Memory usage: {ram_pct}% (threshold {ram_thresh}%)"})
    if hung:
        alerts.append({"type": "hung", "level": "danger", "message": f"{len(hung)} application(s) currently not responding", "apps": hung})
        
    return {
        "timestamp": iso_time,
        "cpu_percent": cpu_pct,
        "ram_percent": ram_pct,
        "ram_used_gb": round((vm.total - vm.available) / (1024**3), 1),
        "ram_total_gb": round(vm.total / (1024**3), 1),
        "net_in_kb_s": max(0.0, net_in_kb),
        "net_out_kb_s": max(0.0, net_out_kb),
        "hung_apps": hung,
        "alerts": alerts
    }

def get_history():
    """Retrieve full history for graphing in frontend."""
    with _history_lock:
        return {
            "labels": list(_timestamps),
            "cpu": list(_cpu_history),
            "ram": list(_ram_history),
            "net_in": list(_net_in_history),
            "net_out": list(_net_out_history)
        }

def get_top_processes(limit=15):
    """Retrieve live active processes sorted by memory and CPU."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "memory_info", "status"]):
        try:
            info = p.info
            mem_mb = round((info.get("memory_info").rss if info.get("memory_info") else 0) / (1024**2), 1)
            procs.append({
                "pid": info["pid"],
                "name": info["name"] or "Unknown",
                "cpu_percent": round(info.get("cpu_percent") or 0.0, 1),
                "mem_percent": round(info.get("memory_percent") or 0.0, 1),
                "mem_mb": mem_mb,
                "status": info.get("status") or "running"
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return sorted(procs, key=lambda x: (x["cpu_percent"], x["mem_percent"]), reverse=True)[:limit]

def _background_loop():
    while not _stop_event.is_set():
        try:
            sample_metrics()
        except Exception:
            pass
        _stop_event.wait(2.0)

def start_background_monitoring():
    """Start background sampling thread if not already running."""
    global _monitor_thread
    if _monitor_thread is None or not _monitor_thread.is_alive():
        _stop_event.clear()
        _monitor_thread = threading.Thread(target=_background_loop, daemon=True, name="SelfHealMonitorThread")
        _monitor_thread.start()

def stop_background_monitoring():
    """Signal background thread to stop."""
    _stop_event.set()

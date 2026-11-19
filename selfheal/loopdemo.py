"""Infinite-loop demo: a REAL runaway process is started, watched, and
terminated. Only the PID we created is ever touched."""
import multiprocessing as mp, time, psutil

def _runaway():
    while True:      # intentional infinite loop, isolated in its own process
        pass

def run_demo(cpu_limit=80.0, timeout=8.0):
    steps = []
    proc = mp.get_context("spawn").Process(target=_runaway, daemon=True)
    proc.start()
    steps.append(f"Started runaway process PID {proc.pid}")
    ps, start, reason = psutil.Process(proc.pid), time.time(), None
    ps.cpu_percent(None)
    while time.time()-start < timeout:
        time.sleep(0.5)
        cpu = ps.cpu_percent(None)
        if cpu >= cpu_limit:
            reason = f"CPU {cpu:.0f}% >= {cpu_limit:.0f}%"; break
    if reason is None:
        reason = f"Timeout after {timeout}s"
    steps.append(f"DETECTED: {reason}")
    proc.terminate(); proc.join(3)
    if proc.is_alive():
        proc.kill(); proc.join(3)
    steps.append(f"TERMINATED: PID {proc.pid}")
    verified = not proc.is_alive()
    steps.append("VERIFIED: process no longer running" if verified else "VERIFY FAILED")
    return {"ok": verified, "pid": proc.pid, "steps": steps}

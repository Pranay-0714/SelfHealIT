"""SelfHeal IT - Enterprise PC Health Platform.
Flask entry point and API router.
Binds to localhost by default, supporting multi-PC agents and browser extensions."""
import os, json
from flask import Flask, jsonify, render_template, request, Response
from selfheal import (
    scanner, chatbot, healing, loopdemo, reports,
    monitoring, security, browser_protection, fleet, config
)

app = Flask(__name__)
STATE = {"scan": None}

# Initialize background monitoring thread
monitoring.start_background_monitoring()

# ==================== WEB DASHBOARD ====================
@app.get("/")
def index():
    return render_template("index.html")

# ==================== PC SCANNER ====================
@app.post("/api/scan")
def api_scan():
    """Execute a comprehensive system scan."""
    STATE["scan"] = scanner.scan()
    return jsonify(STATE["scan"])

@app.get("/api/scan/latest")
def api_scan_latest():
    """Retrieve current or cached scan data."""
    if STATE["scan"] is None:
        STATE["scan"] = scanner.scan()
    return jsonify(STATE["scan"])

# ==================== AI ASSISTANT ====================
@app.post("/api/chat")
def api_chat():
    """AI Assistant query grounded in live scan data."""
    body = request.get_json(silent=True) or {}
    q = body.get("question", "").strip()
    if not q:
        return jsonify({"error": "Empty question"}), 400
    if STATE["scan"] is None:
        STATE["scan"] = scanner.scan()
    return jsonify(chatbot.ask(q, STATE["scan"]))

@app.post("/api/chat/compatibility")
def api_compatibility():
    """Check hardware compatibility against target game or professional software."""
    body = request.get_json(silent=True) or {}
    title = body.get("title", "").strip()
    if not title:
        return jsonify({"error": "No title specified"}), 400
    if STATE["scan"] is None:
        STATE["scan"] = scanner.scan()
    return jsonify(chatbot.check_compatibility(title, STATE["scan"]))

@app.get("/api/chat/bottlenecks")
def api_bottlenecks():
    """Analyze primary system hardware bottlenecks."""
    if STATE["scan"] is None:
        STATE["scan"] = scanner.scan()
    analysis = chatbot.analyze_bottlenecks(STATE["scan"])
    return jsonify({"bottlenecks": analysis})

# ==================== LIVE MONITORING ====================
@app.get("/api/monitoring/stats")
def api_monitoring_stats():
    """Fetch live real-time metrics and alerts."""
    return jsonify(monitoring.sample_metrics())

@app.get("/api/monitoring/history")
def api_monitoring_history():
    """Fetch rolling metrics history for live dashboard charts."""
    return jsonify(monitoring.get_history())

@app.get("/api/monitoring/hung-apps")
def api_hung_apps():
    """Detect frozen or unresponsive application windows."""
    return jsonify(monitoring.get_hung_windows())

@app.get("/api/monitoring/processes")
def api_monitoring_processes():
    """Fetch live active processes sorted by CPU and memory."""
    limit = int(request.args.get("limit", 15))
    return jsonify(monitoring.get_top_processes(limit))

# ==================== SAFE SELF-HEALING ====================
@app.get("/api/heal/actions")
def api_heal_actions():
    """List all predefined safe self-healing actions."""
    return jsonify(healing.list_actions())

@app.post("/api/heal")
def api_heal():
    """Execute a predefined, user-confirmed recovery action."""
    d = request.get_json(silent=True) or {}
    action_name = d.get("action")
    confirmed = d.get("confirmed") is True
    target_pid = d.get("target_pid")
    return jsonify(healing.run_action(action_name, confirmed, target_pid=target_pid))

@app.get("/api/heal/logs")
def api_heal_logs():
    """Retrieve permanent activity audit log."""
    return jsonify(healing.get_activity_logs())

@app.post("/api/loop-demo")
def api_loop():
    """Run real runaway infinite-loop detection demo."""
    return jsonify(loopdemo.run_demo())

# ==================== SECURITY & DEFENDER ====================
@app.get("/api/security/status")
def api_security_status():
    """Query Windows Defender, suspicious processes, and open ports."""
    defend = security.get_defender_status()
    suspicious = security.audit_suspicious_processes()
    ports = security.audit_network_ports()
    return jsonify({
        "defender": defend,
        "suspicious_processes": suspicious,
        "ports": ports
    })

@app.post("/api/security/quick-scan")
def api_security_quick_scan():
    """Trigger a Windows Defender Quick Scan upon user confirmation."""
    d = request.get_json(silent=True) or {}
    confirmed = d.get("confirmed") is True
    return jsonify(security.trigger_defender_scan("QuickScan", confirmed))

# ==================== BROWSER PROTECTION ====================
@app.post("/api/browser/check-url")
def api_browser_check():
    """Validate a URL against phishing and malicious heuristics."""
    d = request.get_json(silent=True) or {}
    url = d.get("url", "").strip()
    return jsonify(browser_protection.analyze_url(url))

# ==================== MULTI-PC AGENTS ====================
@app.post("/api/agent/report")
def api_agent_report():
    """Ingest telemetry heartbeat from a remote agent with Bearer authentication."""
    auth_header = request.headers.get("Authorization", "")
    if not fleet.authenticate_agent(auth_header):
        return jsonify({"error": "Unauthorized. Invalid agent token."}), 401
    
    data = request.get_json(silent=True) or {}
    remote_ip = request.remote_addr or "127.0.0.1"
    recorded = fleet.record_heartbeat(data, remote_ip)
    return jsonify({"ok": True, "message": f"Heartbeat recorded for {recorded['hostname']}", "node": recorded})

@app.get("/api/agent/fleet")
def api_agent_fleet():
    """List all computers enrolled in the fleet."""
    return jsonify(fleet.get_fleet_summary())

@app.delete("/api/agent/<hostname>")
def api_agent_delete(hostname):
    """Remove a decommissioned machine from the fleet list."""
    ok = fleet.remove_agent(hostname)
    return jsonify({"ok": ok})

# ==================== EXPORT REPORTS ====================
@app.get("/api/export/<fmt>")
def api_export(fmt):
    """Export diagnostic report to JSON or PDF format."""
    if not STATE["scan"]:
        STATE["scan"] = scanner.scan()
    if fmt == "json":
        return Response(
            reports.to_json(STATE["scan"]),
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=selfheal_report.json"}
        )
    if fmt == "pdf":
        return Response(
            reports.to_pdf(STATE["scan"]),
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment; filename=selfheal_report.pdf"}
        )
    return jsonify({"error": "Invalid format (use json or pdf)"}), 400

# ==================== SETTINGS & CONFIG ====================
@app.get("/api/settings")
def api_settings_get():
    """Get sanitized settings safe for display."""
    return jsonify(config.get_public_config())

@app.post("/api/settings")
def api_settings_post():
    """Update settings (API keys, alert thresholds, tokens)."""
    d = request.get_json(silent=True) or {}
    updated = config.save_config(d)
    return jsonify({"ok": True, "settings": config.get_public_config()})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Bind to 0.0.0.0 so remote agents on the same local network can report telemetry
    app.run(host="0.0.0.0", port=port, debug=False)

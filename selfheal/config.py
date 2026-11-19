"""SelfHeal IT - Central Configuration & Environment Manager.
Handles API keys, alert thresholds, agent authentication, and local persistence."""
import os, json

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "reports", "settings.json")

DEFAULT_CONFIG = {
    "gemini_api_key": "",
    "openai_api_key": "",
    "anthropic_api_key": "",
    "default_model": "rule-based",  # rule-based, gemini, openai, anthropic
    "agent_secret_key": "selfheal-agent-default-secret-token-key",
    "cpu_alert_threshold": 85,
    "ram_alert_threshold": 85,
    "disk_alert_threshold": 90,
    "monitoring_interval_ms": 2000,
    "auto_refresh_scan": False,
    "theme": "dark"
}

def load_config():
    """Load config from disk with fallback to defaults and env vars."""
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config.update(saved)
        except Exception:
            pass

    # Environment variables override config file if present
    if os.environ.get("GEMINI_API_KEY"):
        config["gemini_api_key"] = os.environ.get("GEMINI_API_KEY")
    if os.environ.get("OPENAI_API_KEY"):
        config["openai_api_key"] = os.environ.get("OPENAI_API_KEY")
    if os.environ.get("ANTHROPIC_API_KEY"):
        config["anthropic_api_key"] = os.environ.get("ANTHROPIC_API_KEY")
    if os.environ.get("AGENT_SECRET_KEY"):
        config["agent_secret_key"] = os.environ.get("AGENT_SECRET_KEY")

    return config

def save_config(new_settings):
    """Save updated settings while preserving existing keys if not provided."""
    config = load_config()
    for k, v in new_settings.items():
        if k in DEFAULT_CONFIG and v is not None:
            # If masked value sent from UI, do not overwrite existing key
            if k.endswith("_key") and isinstance(v, str) and v.startswith("••••"):
                continue
            config[k] = v

    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    return config

def get_public_config():
    """Returns configuration safe for frontend consumption (masks sensitive keys)."""
    cfg = load_config()
    safe = dict(cfg)
    for k in ("gemini_api_key", "openai_api_key", "anthropic_api_key", "agent_secret_key"):
        val = safe.get(k) or ""
        if val:
            safe[k + "_masked"] = f"••••••••{val[-4:]}" if len(val) >= 4 else "••••"
            safe[k + "_set"] = True
        else:
            safe[k + "_masked"] = ""
            safe[k + "_set"] = False
        safe.pop(k, None)
    return safe

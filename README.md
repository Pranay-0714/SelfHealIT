# SelfHeal IT — Windows PC Health & Autonomous Recovery Platform

[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-blue.svg)](https://microsoft.com)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![Framework: Flask](https://img.shields.io/badge/Backend-Flask%203.x-lightgrey.svg)](https://palletsprojects.com/p/flask/)
[![Tests: 62 Passing](https://img.shields.io/badge/Tests-62%20Passed-success.svg)](tests/)

**SelfHeal IT** is an enterprise-grade Windows PC health diagnostics, real-time monitoring, AI-powered troubleshooting, and safe self-healing recovery platform. Built with Python, Flask, modern responsive HTML5/CSS3, and vanilla JavaScript (zero external CDN dependencies).

---

## Key Core Features

### 1. 🖥️ Comprehensive PC Health Scanner (100% Read-Only)
- **Hardware Telemetry**: Deep inspection of CPU (per-core load, clock speed, logical/physical core counts), RAM (utilization, active memory, safe swap/pagefile error handling), GPU (via Windows PowerShell CIM `Win32_VideoController` for VRAM, driver versions, and adapter models), and Storage (all partitions, filesystems, free/used GB).
- **Process & Network Auditing**: Top memory/CPU consumers, active network sockets (established, listening, time_wait), and Wi-Fi interface signal strength and encryption.
- **Diagnostic Finding Engine**: Categorizes issues with Severity (`HIGH`, `MEDIUM`, `LOW`), Root Cause, Real-World Consequence, Recommended Solution, Recovery expectations, and optional 1-click self-healing hooks.
- **Health Score**: Dynamic 0–100 health rating derived from hardware metrics and active findings.

### 2. 🤖 Scan-Grounded AI Assistant & Compatibility Checker
- **Zero-Hallucination Intelligence**: Grounded strictly in real scan telemetry. Discloses hardware limitations transparently.
- **Multi-Provider Support**: Supports **Google Gemini** (`GEMINI_API_KEY`), **OpenAI** (`OPENAI_API_KEY`), **Anthropic** (`ANTHROPIC_API_KEY`), and an advanced **Offline Rule-Based Heuristic Engine** that requires no API keys.
- **Game & Software Compatibility Engine**: Tests your actual CPU cores, RAM, GPU VRAM, and storage against 25+ popular games (Valorant, GTA V, Cyberpunk 2077, Fortnite, Minecraft, CS2, Elden Ring, etc.) and workstation software (Blender, Adobe Premiere Pro, Photoshop, Docker, Android Studio, Unreal Engine).
- **Bottleneck Diagnosis**: Pinpoints whether your CPU, GPU, RAM capacity, or storage I/O is the primary bottleneck.

### 3. 📊 Live Real-Time Monitoring
- **Rolling Canvas Graphs**: Zero-dependency HTML5 Canvas rendering dual-line graphs of CPU and RAM utilization over a rolling 60-sample window.
- **Network Throughput**: Real-time download/upload speed gauges (KB/s).
- **Unresponsive App Detector**: Native Windows C API integration (`user32.IsHungAppWindow` via `ctypes`) detects frozen or hung application windows in sub-milliseconds without system lag.
- **Infinite-Loop Tester**: Real isolated runaway loop demo that safely spawns an infinite CPU loop, detects the spike, terminates strictly that PID, and verifies termination.

### 4. 🩹 Safe, User-Approved Self-Healing
- **Predefined Safe Action Registry**:
  - `clean_temp`: Safely deletes files older than 24 hours from the Windows Temp directory, preserving active/locked files.
  - `flush_dns`: Purges corrupted DNS resolver entries using `ipconfig /flushdns`.
  - `clear_print_spooler`: Cycles the Windows `spoolsv` background service to clear stuck printer queues.
  - `empty_recycle_bin`: Purges the Windows Recycle Bin using native `SHEmptyRecycleBinW` API.
  - `reset_network`: Releases and renews DHCP IP configuration.
  - `restart_unresponsive_app`: Safely terminates frozen processes approved by the user. Protected Windows system binaries (`svchost.exe`, `explorer.exe`, `services.exe`) cannot be killed.
- **Safety Principles**: Scans are read-only by default. Actions require explicit confirmation (`confirmed: true`), run pre-checks, execute whitelisted routines, verify post-execution status, and record full audit entries to `reports/activity_log.jsonl`. No arbitrary shell commands are ever accepted.

### 5. 🔒 Security & Microsoft Defender
- **Defender Telemetry**: Queries Real-Time Protection status, Antivirus engine state, signature version, and definition age.
- **One-Click Defender Quick Scan**: Safely invokes `Start-MpScan -ScanType QuickScan` upon user approval.
- **Suspicious Process Inspector**: Detects executables launching from temp/downloads/untrusted directories or masquerading with Windows system names.
- **Open Ports & Sockets Audit**: Lists all listening ports mapped to PIDs and flags well-known high-risk ports (SMB 445, RDP 3389, Telnet 23).

### 6. 🌐 Browser Protection (Chrome & Edge Extension)
- **Manifest V3 Extension**: Packaged in `browser_extension/`, ready to load into Google Chrome, Microsoft Edge, or Brave.
- **Heuristic Threat Detection**: Detects direct IP hosts, Punycode/IDN homoglyph lookalikes (`xn--`), suspicious TLDs (`.xyz`, `.top`, `.tk`), and deceptive brand subdomains (`paypal.verify-account...`).
- **Connected & Offline Fallback**: Verifies URLs via the local backend `POST /api/browser/check-url` and seamlessly switches to local heuristics when offline.
- **In-Page Safety Warning**: Injects an alert banner on flagged malicious pages allowing users to leave safely.

### 7. 🏢 Multi-PC Fleet Management
- **Central Dashboard**: Tracks all enrolled computers on your local network (online/offline status, health score, CPU %, RAM %, and active alerts).
- **Standalone Remote Agent**: Lightweight script (`agent/selfheal_agent.py`) deployable on secondary PCs.
- **Bearer Token Security**: Telemetry submission requires pre-shared secret authentication (`Authorization: Bearer <TOKEN>`).

### 8. 📑 Diagnostic Reports & JSON Export
- **PDF Generation**: Pure-Python, dependency-free multi-page PDF 1.4 report generator (`/api/export/pdf`). Includes system specs, findings, security status, and transparency disclosures.
- **JSON Telemetry Dump**: Full structured machine-readable JSON (`/api/export/json`).

---

## Project Structure

```
SelfHealIT/
├── app.py                     # Flask application & API routes (binds to 0.0.0.0:5000)
├── requirements.txt           # Python package dependencies
├── README.md                  # Complete documentation and user manual
├── selfheal/                  # Modular backend subsystem
│   ├── __init__.py
│   ├── config.py              # Configuration manager (.env, API keys, thresholds, tokens)
│   ├── scanner.py             # Read-only hardware & OS scanner with safe swap handling
│   ├── chatbot.py             # Grounded AI assistant (Gemini/OpenAI/Anthropic/Rule-based)
│   ├── monitoring.py          # Real-time metrics streaming & ctypes hung app detection
│   ├── healing.py             # Predefined verified safe actions + activity audit trail
│   ├── security.py            # Windows Defender status, suspicious processes & port scan
│   ├── browser_protection.py  # Phishing & malicious URL heuristics engine
│   ├── fleet.py               # Multi-PC fleet registry & heartbeat ingestion
│   ├── reports.py             # Pure-Python multi-page PDF & JSON report writers
│   └── loopdemo.py            # Real runaway loop demo (spawn -> detect -> terminate -> verify)
├── static/
│   ├── css/
│   │   └── dashboard.css      # Modern dark-mode styling, responsive grid, badges
│   ├── js/
│   │   └── dashboard.js       # SPA controller, real-time charts, tab management
│   ├── style.css              # Legacy styles preserved
│   └── app.js                 # Legacy bindings preserved
├── templates/
│   └── index.html             # Unified modern dashboard (Scanner, AI, Monitoring, Healing, etc.)
├── browser_extension/         # Chrome & Microsoft Edge Manifest V3 Extension
│   ├── manifest.json
│   ├── background.js          # Service worker for URL checking
│   ├── content.js             # Phishing warning banner injector
│   ├── popup.html             # Extension popup UI
│   ├── popup.js               # Extension popup controller
│   ├── README.md              # Installation instructions
│   └── icons/                 # Clean 16px, 48px, 128px shield icons
├── agent/                     # Standalone Multi-PC Remote Agent
│   ├── selfheal_agent.py      # Telemetry sender script
│   └── README.md              # Setup guide for Windows Startup / Task Scheduler
├── reports/
│   ├── activity_log.jsonl     # Permanent recovery action audit log
│   └── fleet.json             # Enrolled fleet machines registry
└── tests/                     # 62 Automated Unit & Integration Tests
    ├── test_basic.py          # Original 10 test suite preserved
    ├── test_scanner.py        # Deep scanner & swap error handling tests
    ├── test_chatbot.py        # Compatibility & bottleneck unit tests
    ├── test_healing.py        # Whitelist, verification, and logging tests
    ├── test_security.py       # Defender status & port audit tests
    ├── test_browser.py        # Phishing heuristics & URL analysis tests
    ├── test_fleet.py          # Multi-PC token authentication & heartbeat tests
    └── test_api.py            # Comprehensive Flask REST endpoint tests
```

---

## Installation & Setup

### 1. Prerequisites
- **Operating System**: Windows 10 or Windows 11 (64-bit recommended)
- **Python**: Python 3.10, 3.11, 3.12, 3.13, or 3.14

### 2. Install Dependencies
Open PowerShell or Command Prompt in the project folder:
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Launch SelfHeal IT
```powershell
python app.py
```
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## Running the Automated Test Suite

Run the full suite of 62 unit and integration tests:
```powershell
python -m unittest discover -s tests
```
*Expected output:*
```
..............................................................
----------------------------------------------------------------------
Ran 62 tests in ~70s

OK
```

---

## Browser Extension Setup (Chrome & Edge)

1. Open **Microsoft Edge** (`edge://extensions`) or **Google Chrome** (`chrome://extensions`).
2. Enable **Developer mode** toggle.
3. Click **Load unpacked**.
4. Select the `browser_extension` folder located inside the SelfHeal IT directory.
5. The **SelfHeal IT Browser Protection** shield will appear in your browser toolbar.

---

## Multi-PC Agent Deployment

To monitor additional computers on your home or office local network:
1. Copy `agent/selfheal_agent.py` to the target computer.
2. Ensure Python and `psutil` are installed (`pip install psutil`).
3. Run:
   ```bash
   python selfheal_agent.py http://<SERVER-IP>:5000/api/agent/report selfheal-agent-default-secret-token-key
   ```
4. The remote machine will automatically appear in the **Multi-PC Fleet** tab.

---

## API & Configuration

Settings can be customized either via the **Settings tab** in the dashboard UI or by setting environment variables:
- `GEMINI_API_KEY`: Google Gemini API key for advanced AI analysis.
- `OPENAI_API_KEY`: OpenAI API key.
- `ANTHROPIC_API_KEY`: Anthropic Claude API key.
- `AGENT_SECRET_KEY`: Custom secret token for Multi-PC fleet agents.
- `PORT`: Web server port (defaults to `5000`).

---

## Safety & Transparency Disclosures

1. **Read-Only Scanning**: Health and security scans do not modify files, registry keys, or services.
2. **Explicit Confirmation**: Every self-healing action requires user confirmation (`confirmed: true`).
3. **No Arbitrary Execution**: SelfHeal IT only executes whitelisted, predefined recovery routines.
4. **Permanent Audit Trail**: All actions are logged with timestamps, parameters, and verification status in `reports/activity_log.jsonl`.
5. **Antivirus Complement**: SelfHeal IT is a PC health and diagnostic platform; it coordinates with but does not replace Windows Defender.
6. **No Crash Recovery Promises**: SelfHeal IT does not promise recovery of unsaved work in frozen applications or uncommitted data from system crashes.

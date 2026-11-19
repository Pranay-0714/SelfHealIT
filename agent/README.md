# SelfHeal IT — Remote Multi-PC Agent

The **SelfHeal IT Remote Agent** is a lightweight Python background service that reports the hardware health, resource utilization, and diagnostic findings of secondary computers to the central SelfHeal IT platform.

---

## Requirements

- Python 3.8 or newer
- `psutil` library:
  ```bash
  pip install psutil
  ```

---

## Running the Agent

### Method 1: Command Line
```bash
python selfheal_agent.py http://<CENTRAL-SERVER-IP>:5000/api/agent/report <AGENT_SECRET_KEY>
```

**Example:**
```bash
python selfheal_agent.py http://192.168.1.50:5000/api/agent/report selfheal-agent-default-secret-token-key
```

### Method 2: Environment Variables
```bash
export SELFHEAL_SERVER="http://192.168.1.50:5000/api/agent/report"
export SELFHEAL_SECRET="your-configured-token"
python selfheal_agent.py
```

---

## Setting up Auto-Start on Windows

### Option A: Windows Startup Folder
1. Create a shortcut to `pythonw.exe selfheal_agent.py`
2. Press `Win + R`, type `shell:startup` and press Enter.
3. Paste the shortcut into the Startup folder.

### Option B: Windows Task Scheduler
1. Open **Task Scheduler** (`taskschd.msc`).
2. Click **Create Basic Task** -> Name it `SelfHeal Agent`.
3. Set trigger to **When I log on**.
4. Set action to **Start a Program**:
   - Program/script: `python.exe`
   - Arguments: `selfheal_agent.py http://192.168.1.50:5000/api/agent/report your-secret-token`
   - Start in: `<folder where agent is saved>`
5. Check **Run with highest privileges** if desired.

---

## Security
All telemetry transmitted between the agent and the server is protected by the pre-shared secret token in the `Authorization: Bearer <TOKEN>` header. Unauthorized submissions are rejected with HTTP 401.

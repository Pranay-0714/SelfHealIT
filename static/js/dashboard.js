/**
 * SelfHeal IT - Enterprise PC Health Platform Frontend Controller
 */

// Utility Helpers
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const post = (url, body) => fetch(url, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body || {})
}).then(r => r.json());
const get = url => fetch(url).then(r => r.json());

// Global State
let CURRENT_SCAN = null;
let PENDING_ACTION = null;
let MONITOR_INTERVAL = null;

// Tab Switching
function switchTab(tabId) {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.getAttribute('data-tab') === tabId);
  });
  document.querySelectorAll('.tab-content').forEach(el => {
    el.classList.toggle('active', el.id === tabId);
  });

  const titles = {
    'tab-scanner': 'PC Health Scanner',
    'tab-assistant': 'AI Assistant & Troubleshooting',
    'tab-monitoring': 'Live Real-Time Monitoring',
    'tab-healing': 'Safe Self-Healing Actions',
    'tab-security': 'Security & Windows Defender',
    'tab-network': 'Network & Diagnostics',
    'tab-multipc': 'Multi-PC Fleet Management',
    'tab-reports': 'Health Reports & Export',
    'tab-settings': 'Settings & API Keys'
  };
  $('page-title').textContent = titles[tabId] || 'SelfHeal IT';

  if (tabId === 'tab-security') loadSecurityData();
  if (tabId === 'tab-healing') loadHealingLogs();
  if (tabId === 'tab-multipc') loadFleetData();
  if (tabId === 'tab-settings') loadSettings();
}

document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => switchTab(item.getAttribute('data-tab')));
});

// ==================== 1. SCANNER CONTROLLER ====================
async function runScan() {
  const btn = $('btn-top-scan');
  btn.disabled = true;
  btn.innerHTML = 'Scanning System...';

  try {
    const data = await post('/api/scan');
    CURRENT_SCAN = data;
    renderScanData(data);
  } catch (err) {
    alert('Scan error: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:15px;height:15px;"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg> Run System Scan';
  }
}

async function loadLatestScan() {
  try {
    const data = await get('/api/scan/latest');
    CURRENT_SCAN = data;
    renderScanData(data);
  } catch (err) {
    console.error('Failed to load initial scan', err);
  }
}

function renderScanData(d) {
  if (!d) return;

  // 1. Health Score Gauge
  const score = d.health_score != null ? d.health_score : 100;
  const gauge = $('health-score-gauge');
  gauge.textContent = score;
  gauge.className = 'score-badge';
  if (score >= 80) {
    $('health-score-verdict').textContent = 'Optimal Condition';
    $('health-score-verdict').style.color = '#10b981';
  } else if (score >= 60) {
    gauge.classList.add('score-warning');
    $('health-score-verdict').textContent = 'Attention Recommended';
    $('health-score-verdict').style.color = '#f59e0b';
  } else {
    gauge.classList.add('score-danger');
    $('health-score-verdict').textContent = 'Critical Issues Detected';
    $('health-score-verdict').style.color = '#f43f5e';
  }
  $('health-score-sub').textContent = `${d.findings ? d.findings.length : 0} issue(s) identified`;

  // 2. CPU Card
  const cpuPct = d.cpu.usage_percent;
  $('cpu-load-badge').textContent = `${cpuPct}%`;
  $('card-cpu-name').textContent = d.cpu.name || 'Processor';
  $('card-cpu-sub').textContent = `${d.cpu.physical_cores} Cores / ${d.cpu.logical_cores} Threads`;
  const cpuFill = $('cpu-progress');
  cpuFill.style.width = `${Math.min(100, cpuPct)}%`;
  cpuFill.className = 'progress-fill ' + (cpuPct > 85 ? 'fill-rose' : cpuPct > 70 ? 'fill-amber' : 'fill-green');

  // 3. RAM Card
  const ramPct = d.ram.percent;
  $('ram-pct-badge').textContent = `${ramPct}%`;
  $('card-ram-val').textContent = `${d.ram.used_gb || (d.ram.total_gb - d.ram.available_gb).toFixed(1)} GB / ${d.ram.total_gb} GB`;
  $('card-ram-sub').textContent = `Available: ${d.ram.available_gb} GB`;
  const ramFill = $('ram-progress');
  ramFill.style.width = `${Math.min(100, ramPct)}%`;
  ramFill.className = 'progress-fill ' + (ramPct > 85 ? 'fill-rose' : ramPct > 70 ? 'fill-amber' : 'fill-green');

  // 4. Primary Storage Card
  if (d.disks && d.disks.length > 0) {
    const primary = d.disks[0];
    $('disk-pct-badge').textContent = `${primary.percent}%`;
    $('card-disk-val').textContent = `${primary.free_gb} GB Free`;
    $('card-disk-sub').textContent = `Drive ${primary.mount} (${primary.total_gb} GB Total)`;
    const diskFill = $('disk-progress');
    diskFill.style.width = `${Math.min(100, primary.percent)}%`;
    diskFill.className = 'progress-fill ' + (primary.percent > 90 ? 'fill-rose' : primary.percent > 75 ? 'fill-amber' : 'fill-green');
  }

  // 5. Hardware Identity Specs
  $('spec-os').textContent = `${d.os.system} ${d.os.release} (${d.os.architecture || 'x64'})`;
  $('spec-gpu').textContent = d.gpu || 'Generic Display Adapter';
  $('spec-uptime').textContent = `${d.os.uptime_hours} hrs (${(d.os.uptime_hours/24).toFixed(1)} days)`;
  $('spec-procs').textContent = `${d.process_count || (d.top_processes ? d.top_processes.length : 0)} running`;
  
  if (d.wifi && d.wifi.available) {
    $('spec-wifi').textContent = `${d.wifi.SSID || 'Connected'} (${d.wifi.Signal || 'OK'})`;
  } else {
    $('spec-wifi').textContent = 'Ethernet / Local';
  }

  if (d.battery && d.battery.present) {
    $('spec-power').textContent = `${d.battery.percent}% (${d.battery.plugged ? 'AC Connected' : 'On Battery'})`;
  } else {
    $('spec-power').textContent = 'Desktop AC Power';
  }

  // 6. Alert Banner for Hung Windows
  if (d.hung_apps && d.hung_apps.length > 0) {
    $('scanner-alert').style.display = 'flex';
    $('scanner-alert-msg').innerHTML = `Detected ${d.hung_apps.length} frozen application window(s): <b>${esc(d.hung_apps[0].name)}</b> (PID ${d.hung_apps[0].pid}).`;
  } else {
    $('scanner-alert').style.display = 'none';
  }

  // 7. Findings List
  const container = $('findings-container');
  const findings = d.findings || [];
  $('findings-count').textContent = findings.length;

  if (findings.length === 0) {
    container.innerHTML = `<div class="card" style="text-align: center; color: var(--emerald-primary); padding: 26px;">
      <b>All System Health Checks Passed</b><br>
      <span style="font-size: 13px; color: var(--text-muted);">No hardware, storage, or critical performance anomalies detected.</span>
    </div>`;
  } else {
    container.innerHTML = findings.map((f, i) => {
      const sevClass = f.severity === 'high' ? 'finding-high' : f.severity === 'medium' ? 'finding-medium' : 'finding-low';
      const badgeClass = f.severity === 'high' ? 'badge-high' : f.severity === 'medium' ? 'badge-medium' : 'badge-low';
      const healBtn = f.heal_action ? `
        <div class="finding-actions">
          <button class="btn btn-primary btn-sm" onclick="promptHealAction('${f.heal_action}', '${esc(f.problem)}', ${f.target_pid || 'null'})">
            Action: ${esc(f.heal_action)}
          </button>
        </div>` : '';

      return `
        <div class="finding-item ${sevClass}">
          <div class="finding-header">
            <span class="finding-title">${esc(f.problem)}</span>
            <span class="badge ${badgeClass}">${esc(f.severity)}</span>
          </div>
          <div class="finding-body">
            <b>Cause:</b> ${esc(f.cause)}<br>
            <b>Consequence:</b> ${esc(f.consequence)}<br>
            <b>Solution:</b> ${esc(f.solution)}<br>
            <b>Recovery Expectation:</b> ${esc(f.recovery)}
          </div>
          ${healBtn}
        </div>
      `;
    }).join('');
  }

  // Also update Network Tab Wi-Fi info
  if ($('net-wifi-ssid')) {
    $('net-wifi-ssid').textContent = (d.wifi && d.wifi.SSID) ? d.wifi.SSID : 'Ethernet / Local';
    $('net-wifi-details').textContent = (d.wifi && d.wifi.Signal) ? `Signal: ${d.wifi.Signal} | Radio: ${d.wifi['Radio type'] || 'N/A'}` : 'Wired LAN Adapter';
    if (d.network) {
      $('net-established-val').textContent = `${d.network.established || 0} Established`;
      $('net-listening-val').textContent = `${d.network.listening || 0} Listening ports`;
    }
  }

  // Update Report preview
  if ($('report-preview-box')) {
    $('report-preview-box').textContent = JSON.stringify(d, null, 2);
  }
}

// ==================== 2. AI ASSISTANT CONTROLLER ====================
async function sendChatMessage() {
  const input = $('chat-input');
  const q = input.value.trim();
  if (!q) return;

  input.value = '';
  appendChatMsg('user', q);

  const botBubble = appendChatMsg('bot', 'Analyzing real PC scan telemetry...');

  try {
    const res = await post('/api/chat', { question: q });
    const ans = res.answer || res.error || 'No response returned.';
    const source = res.source || 'telemetry-engine';
    botBubble.innerHTML = `<span class="chat-tag">${esc(source)}</span><br>${esc(ans)}`;
  } catch (err) {
    botBubble.textContent = 'Error connecting to assistant: ' + err.message;
  }
}

function sendQuickPrompt(promptText) {
  $('chat-input').value = promptText;
  sendChatMessage();
}

function appendChatMsg(sender, text) {
  const stream = $('chat-stream');
  const div = document.createElement('div');
  div.className = `chat-msg ${sender === 'user' ? 'chat-msg-user' : 'chat-msg-bot'}`;
  div.textContent = text;
  stream.appendChild(div);
  stream.scrollTop = stream.scrollHeight;
  return div;
}

async function askBottlenecks() {
  switchTab('tab-assistant');
  appendChatMsg('user', 'Run a deep diagnostic bottleneck analysis on my hardware.');
  const bot = appendChatMsg('bot', 'Evaluating CPU, GPU, RAM, and Storage balance...');
  try {
    const res = await get('/api/chat/bottlenecks');
    bot.innerHTML = `<span class="chat-tag">Bottleneck Diagnosis</span><br>${esc(res.bottlenecks)}`;
  } catch (e) {
    bot.textContent = 'Failed to evaluate bottlenecks: ' + e.message;
  }
}

// Compatibility Modal
function openCompatibilityModal() {
  $('modal-compatibility').classList.add('active');
}

function syncCompatInput(val) {
  if (val) $('compat-custom-input').value = val;
}

async function runCompatibilityCheck() {
  const title = $('compat-custom-input').value.trim();
  if (!title) return;

  const box = $('compat-results-box');
  box.style.display = 'block';
  box.innerHTML = '<i>Querying hardware specifications vs database...</i>';

  try {
    const res = await post('/api/chat/compatibility', { title });
    if (!res.ok && !res.found) {
      box.innerHTML = `<div style="color: #fbbf24;">${esc(res.message)}</div>
      <div style="margin-top: 8px; font-size: 12px; color: var(--text-muted);">
        Hardware Specs: RAM: ${res.specs.ram_gb} GB | CPU Threads: ${res.specs.logical_cores} | GPU: ${esc(res.specs.gpu)}
      </div>`;
      return;
    }

    const d = res.details;
    const isExceed = res.verdict === 'Exceeds Recommended';
    const isMeet = res.verdict === 'Meets Minimum';
    const color = isExceed ? '#10b981' : isMeet ? '#38bdf8' : '#f43f5e';

    box.innerHTML = `
      <div style="font-size: 15px; font-weight: 700; color: ${color}; margin-bottom: 6px;">
        Verdict: ${esc(res.verdict)}
      </div>
      <p style="margin: 0 0 10px 0; color: #e2e8f0;">${esc(res.summary)}</p>
      <table style="font-size: 12px; width: 100%;">
        <tr><td><b>RAM:</b></td><td>${esc(d.ram.user)}</td><td>Min: ${esc(d.ram.min)} | Rec: ${esc(d.ram.rec)}</td><td>${d.ram.pass ? '<span style="color:#10b981;font-weight:600;">PASS</span>' : '<span style="color:#f43f5e;font-weight:600;">SHORTFALL</span>'}</td></tr>
        <tr><td><b>CPU:</b></td><td>${esc(d.cpu_cores.user)}</td><td>Min: ${esc(d.cpu_cores.min)} | Rec: ${esc(d.cpu_cores.rec)}</td><td>${d.cpu_cores.pass ? '<span style="color:#10b981;font-weight:600;">PASS</span>' : '<span style="color:#f43f5e;font-weight:600;">SHORTFALL</span>'}</td></tr>
        <tr><td><b>GPU:</b></td><td colspan="3">${esc(d.gpu.note)}</td></tr>
      </table>
      ${d.notes ? `<div style="margin-top: 8px; font-size: 11px; color: var(--text-muted);"><b>Note:</b> ${esc(d.notes)}</div>` : ''}
    `;
  } catch (err) {
    box.innerHTML = `<span style="color: #f43f5e;">Check failed: ${err.message}</span>`;
  }
}

// ==================== 3. LIVE MONITORING CONTROLLER ====================
function initLiveMonitoring() {
  if (MONITOR_INTERVAL) clearInterval(MONITOR_INTERVAL);
  fetchMonitoringSnapshot();
  MONITOR_INTERVAL = setInterval(fetchMonitoringSnapshot, 2000);
}

async function fetchMonitoringSnapshot() {
  try {
    const stats = await get('/api/monitoring/stats');
    $('live-cpu-val').textContent = `${stats.cpu_percent}%`;
    $('live-ram-val').textContent = `${stats.ram_percent}%`;
    $('live-ram-sub').textContent = `${stats.ram_used_gb} GB / ${stats.ram_total_gb} GB`;
    $('live-net-in-val').textContent = `${stats.net_in_kb_s} KB/s`;
    $('live-net-out-val').textContent = `${stats.net_out_kb_s} KB/s`;

    // Hung app detection alert
    const hungAlert = $('monitoring-hung-alert');
    if (stats.hung_apps && stats.hung_apps.length > 0) {
      const hung = stats.hung_apps[0];
      hungAlert.style.display = 'flex';
      $('monitoring-hung-text').textContent = ` Process '${hung.name}' (PID ${hung.pid}) is frozen.`;
      $('btn-terminate-hung').onclick = () => promptHealAction('restart_unresponsive_app', `Terminate Process (${hung.name})`, hung.pid);
    } else {
      hungAlert.style.display = 'none';
    }

    // Refresh history and draw canvas
    const hist = await get('/api/monitoring/history');
    drawLiveChart(hist);

    // Refresh processes if tab active
    const procs = await get('/api/monitoring/processes?limit=8');
    renderProcessesTable(procs);
  } catch (err) {
    console.error('Monitoring poll error', err);
  }
}

function renderProcessesTable(procs) {
  const tbody = $('live-processes-tbody');
  if (!tbody || !procs) return;

  tbody.innerHTML = procs.map(p => `
    <tr>
      <td><code>${p.pid}</code></td>
      <td><b>${esc(p.name)}</b></td>
      <td><span style="color: ${p.cpu_percent > 50 ? '#f43f5e' : '#38bdf8'}; font-weight: 600;">${p.cpu_percent}%</span></td>
      <td>${p.mem_percent}%</td>
      <td>${p.mem_mb} MB</td>
      <td><span class="status-indicator" style="font-size: 10px;">${esc(p.status)}</span></td>
    </tr>
  `).join('');
}

// Lightweight HTML5 Canvas Chart Renderer (Zero CDN dependencies)
function drawLiveChart(data) {
  const canvas = $('chart-cpu-ram');
  if (!canvas || !data || !data.cpu || data.cpu.length === 0) return;

  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();

  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;
  const padBottom = 20;
  const padLeft = 32;
  const plotW = w - padLeft - 10;
  const plotH = h - padBottom - 10;

  ctx.clearRect(0, 0, w, h);

  // Draw Grid Lines (0%, 25%, 50%, 75%, 100%)
  ctx.strokeStyle = '#1e293b';
  ctx.lineWidth = 1;
  ctx.fillStyle = '#64748b';
  ctx.font = '10px -apple-system, sans-serif';

  for (let p = 0; p <= 100; p += 25) {
    const y = 10 + plotH - (p / 100) * plotH;
    ctx.beginPath();
    ctx.moveTo(padLeft, y);
    ctx.lineTo(w - 10, y);
    ctx.stroke();
    ctx.fillText(`${p}%`, 6, y + 3);
  }

  // Draw Series Function
  function drawLine(points, strokeColor) {
    if (points.length < 2) return;
    const step = plotW / Math.max(1, points.length - 1);

    ctx.beginPath();
    points.forEach((val, i) => {
      const x = padLeft + i * step;
      const y = 10 + plotH - (Math.min(100, Math.max(0, val)) / 100) * plotH;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });

    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  // Draw CPU series & RAM series
  drawLine(data.cpu, '#38bdf8');
  drawLine(data.ram, '#6366f1');
}

async function runLoopDemo() {
  const container = $('loop-demo-container');
  const pre = $('loop-demo-output');
  container.style.display = 'block';
  pre.textContent = 'Spawning isolated runaway test process...\nDetecting excessive CPU loop...';

  try {
    const res = await post('/api/loop-demo');
    pre.textContent = (res.steps || []).join('\n');
  } catch (err) {
    pre.textContent = 'Loop demo error: ' + err.message;
  }
}

// ==================== 4. SELF-HEALING CONTROLLER ====================
function promptHealAction(action, title, targetPid = null) {
  PENDING_ACTION = { action, targetPid };
  $('modal-heal-title').textContent = title || `Execute ${action}`;
  $('modal-heal-desc').textContent = `Are you sure you want to run '${action}'? All actions run safe verification routines and record to the permanent activity log.`;

  const pidRow = $('modal-heal-pid-row');
  if (action === 'restart_unresponsive_app') {
    pidRow.style.display = 'block';
    $('modal-heal-pid-input').value = targetPid || '';
  } else {
    pidRow.style.display = 'none';
  }

  $('modal-heal-btn-confirm').onclick = executeConfirmedAction;
  $('modal-heal-confirm').classList.add('active');
}

function promptTerminateAppManual() {
  promptHealAction('restart_unresponsive_app', 'Terminate Process by PID');
}

async function executeConfirmedAction() {
  closeModal('modal-heal-confirm');
  if (!PENDING_ACTION) return;

  const { action, targetPid } = PENDING_ACTION;
  const pid = action === 'restart_unresponsive_app' ? $('modal-heal-pid-input').value.trim() : targetPid;

  try {
    const res = await post('/api/heal', {
      action,
      confirmed: true,
      target_pid: pid
    });

    if (res.ok) {
      alert(`Success: ${res.message || 'Action completed and verified.'}`);
    } else {
      alert(`Notice: ${res.error || res.message || 'Action could not be executed.'}`);
    }

    loadHealingLogs();
    runScan();
  } catch (err) {
    alert('Action execution failure: ' + err.message);
  }
}

async function loadHealingLogs() {
  try {
    const logs = await get('/api/heal/logs');
    const tbody = $('healing-logs-tbody');
    if (!tbody) return;

    if (!logs || logs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No recovery events recorded yet.</td></tr>';
      return;
    }

    tbody.innerHTML = logs.map(l => {
      const isOk = l.verified === true || l.ok === true;
      const statusBadge = isOk
        ? '<span class="status-indicator">Verified</span>'
        : '<span class="status-indicator" style="color: #f43f5e; background: rgba(244, 63, 94, 0.15); border-color: rgba(244, 63, 94, 0.3);">Notice</span>';

      return `
        <tr>
          <td><small>${esc(l.time || '')}</small></td>
          <td><b>${esc(l.event || '')}</b></td>
          <td><code>${esc(l.action || '-')}</code></td>
          <td>${statusBadge}</td>
          <td><small>${esc(l.message || l.error || JSON.stringify(l))}</small></td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to load activity logs', err);
  }
}

// ==================== 5. SECURITY & DEFENDER CONTROLLER ====================
async function loadSecurityData() {
  try {
    const sec = await get('/api/security/status');
    const def = sec.defender || {};

    // 1. Defender card
    const defBadge = $('defender-status-badge');
    if (def.realtime_enabled && def.antivirus_enabled) {
      defBadge.textContent = 'Active & Protected';
      defBadge.className = 'badge badge-low';
    } else {
      defBadge.textContent = 'Attention Needed';
      defBadge.className = 'badge badge-high';
    }

    $('sec-def-realtime').textContent = def.realtime_enabled ? 'Active (Scanning Files)' : 'DISABLED';
    $('sec-def-realtime').style.color = def.realtime_enabled ? '#10b981' : '#f43f5e';
    $('sec-def-service').textContent = def.service_enabled ? 'Running' : 'Inactive';
    $('sec-def-sigver').textContent = def.signature_version || 'Unknown';
    $('sec-def-sigage').textContent = def.signature_age_days != null ? `${def.signature_age_days} day(s) old` : 'Current';

    // 2. Suspicious processes
    const suspList = $('suspicious-procs-list');
    const procs = sec.suspicious_processes || [];
    if (procs.length === 0) {
      suspList.innerHTML = `<div style="color: var(--emerald-primary); font-size: 13px;">No processes exhibiting suspicious directory or masquerading patterns detected.</div>`;
    } else {
      suspList.innerHTML = procs.map(p => `
        <div style="background: rgba(244,63,94,0.1); border-left: 3px solid #f43f5e; padding: 8px 12px; margin-bottom: 8px; border-radius: 4px; font-size: 12.5px;">
          <b>${esc(p.name)} (PID ${p.pid})</b> &mdash; ${esc(p.description)}
        </div>
      `).join('');
    }

    // 3. Ports table
    const ports = (sec.ports && sec.ports.listening) || [];
    $('open-ports-count').textContent = `${ports.length} Open Sockets`;
    const tbody = $('ports-tbody');
    tbody.innerHTML = ports.map(p => `
      <tr>
        <td><b>${p.port}</b></td>
        <td><code>${esc(p.ip)}</code></td>
        <td>${p.pid}</td>
        <td>${esc(p.process)}</td>
        <td>${p.is_risky ? `<span style="color: #f43f5e; font-weight:600;">RISK: ${esc(p.risk_note)}</span>` : '<span style="color: #10b981;">Normal Service</span>'}</td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Security fetch failure', err);
  }
}

function promptDefenderScan() {
  $('modal-defender-confirm').classList.add('active');
}

async function executeDefenderScan() {
  closeModal('modal-defender-confirm');
  try {
    const res = await post('/api/security/quick-scan', { confirmed: true });
    alert(res.message || 'Defender scan initiated.');
  } catch (err) {
    alert('Failed to trigger scan: ' + err.message);
  }
}

// ==================== 6. NETWORK CONTROLLER ====================
async function testUrlSafety() {
  const url = $('net-url-input').value.trim();
  if (!url) return;

  const resDiv = $('net-url-result');
  resDiv.style.display = 'block';
  resDiv.innerHTML = '<i>Analyzing URL against phishing heuristics and threat list...</i>';

  try {
    const data = await post('/api/browser/check-url', { url });
    const isDangerous = data.verdict === 'Dangerous';
    const isSuspicious = data.verdict === 'Suspicious';
    const color = isDangerous ? '#f43f5e' : isSuspicious ? '#f59e0b' : '#10b981';
    const bg = isDangerous ? 'rgba(244,63,94,0.12)' : isSuspicious ? 'rgba(245,158,11,0.12)' : 'rgba(16,185,129,0.12)';

    resDiv.style.background = bg;
    resDiv.style.border = `1px solid ${color}`;
    resDiv.innerHTML = `
      <div style="font-weight: 700; color: ${color}; font-size: 15px; margin-bottom: 4px;">
        Verdict: ${esc(data.verdict)} (Safety Score: ${data.safety_score}/100)
      </div>
      <div>Domain: <b>${esc(data.domain)}</b></div>
      ${data.threats && data.threats.length > 0 ? `
        <div style="margin-top: 8px; font-size: 12px; color: #fda4af;">
          <b>Risk Indicators:</b><br>${data.threats.map(t => `&bull; ${esc(t)}`).join('<br>')}
        </div>
      ` : '<div style="margin-top: 6px; color: #6ee7b7; font-size: 12px;">No malicious or homoglyph patterns detected.</div>'}
    `;
  } catch (e) {
    resDiv.innerHTML = `<span style="color: #f43f5e;">Scan failed: ${e.message}</span>`;
  }
}

// ==================== 7. MULTI-PC FLEET CONTROLLER ====================
async function loadFleetData() {
  try {
    const fleet = await get('/api/agent/fleet');
    const settings = await get('/api/settings');

    if ($('fleet-token-display')) {
      $('fleet-token-display').textContent = settings.agent_secret_key_masked || 'selfheal-agent-default-secret-token-key';
    }

    const grid = $('fleet-grid');
    $('fleet-count').textContent = fleet.length + 1;

    let html = `
      <div class="card" style="background: rgba(255,255,255,0.02);">
        <div style="display: flex; justify-content: space-between;">
          <b>This PC (Host Server)</b>
          <span class="status-indicator"><span class="dot-pulse"></span> Master Node</span>
        </div>
        <div style="font-size: 12px; color: var(--text-muted); margin-top: 6px;">Receives heartbeats and coordinates health diagnostics.</div>
      </div>
    `;

    fleet.forEach(node => {
      const isOnline = node.status === 'Online';
      const statusPill = isOnline
        ? '<span class="status-indicator"><span class="dot-pulse"></span> Online</span>'
        : '<span class="status-indicator" style="color: #94a3b8; background: rgba(255,255,255,0.04);">Offline</span>';

      html += `
        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <b style="font-size: 14px; color: #fff;">${esc(node.hostname)}</b>
            ${statusPill}
          </div>
          <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">
            IP: <code>${esc(node.remote_ip)}</code> | Score: <b style="color: ${node.health_score > 75 ? '#10b981' : '#f59e0b'};">${node.health_score}/100</b>
          </div>
          <div style="font-size: 11.5px; color: #cbd5e1;">
            CPU: ${node.cpu_percent}% | RAM: ${node.ram_percent}% (${node.ram_total_gb} GB)
          </div>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 6px;">
            Last Seen: ${esc(node.last_seen_iso || 'Never')} (${node.seconds_ago}s ago)
          </div>
        </div>
      `;
    });

    grid.innerHTML = html;
  } catch (err) {
    console.error('Fleet load failure', err);
  }
}

// ==================== 9. SETTINGS CONTROLLER ====================
async function loadSettings() {
  try {
    const s = await get('/api/settings');
    if ($('cfg-cpu-thresh')) $('cfg-cpu-thresh').value = s.cpu_alert_threshold || 85;
    if ($('cfg-ram-thresh')) $('cfg-ram-thresh').value = s.ram_alert_threshold || 85;
    if ($('cfg-agent-secret')) $('cfg-agent-secret').value = s.agent_secret_key_masked || '';
    if ($('cfg-gemini') && s.gemini_api_key_set) $('cfg-gemini').placeholder = s.gemini_api_key_masked;
    if ($('cfg-openai') && s.openai_api_key_set) $('cfg-openai').placeholder = s.openai_api_key_masked;
    if ($('cfg-anthropic') && s.anthropic_api_key_set) $('cfg-anthropic').placeholder = s.anthropic_api_key_masked;
  } catch (err) {
    console.error('Settings load error', err);
  }
}

async function saveSettings(e) {
  e.preventDefault();
  const payload = {
    cpu_alert_threshold: parseInt($('cfg-cpu-thresh').value),
    ram_alert_threshold: parseInt($('cfg-ram-thresh').value)
  };

  const secret = $('cfg-agent-secret').value.trim();
  if (secret && !secret.startsWith('••••')) payload.agent_secret_key = secret;

  const gemini = $('cfg-gemini').value.trim();
  if (gemini) payload.gemini_api_key = gemini;

  const openai = $('cfg-openai').value.trim();
  if (openai) payload.openai_api_key = openai;

  const anthropic = $('cfg-anthropic').value.trim();
  if (anthropic) payload.anthropic_api_key = anthropic;

  try {
    await post('/api/settings', payload);
    const status = $('settings-save-status');
    status.textContent = 'Settings saved successfully.';
    setTimeout(() => { status.textContent = ''; }, 3000);
    loadSettings();
  } catch (err) {
    alert('Failed to save settings: ' + err.message);
  }
}

// Modal helper
function closeModal(id) {
  const el = $(id);
  if (el) el.classList.remove('active');
}

// Initialization on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  loadLatestScan();
  initLiveMonitoring();
});

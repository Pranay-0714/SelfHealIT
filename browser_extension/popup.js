const BACKEND_URL = "http://127.0.0.1:5000/api/browser/check-url";

const $ = id => document.getElementById(id);

async function checkBackend() {
  try {
    const res = await fetch("http://127.0.0.1:5000/api/scan/latest", { method: "GET" });
    $("backend-status").textContent = res.ok ? "Local Engine Online" : "Local Engine Alert";
    $("backend-status").style.color = "#4ade80";
  } catch (e) {
    $("backend-status").textContent = "Local Agent Offline (Offline Heuristics Active)";
    $("backend-status").style.color = "#f59e0b";
  }
}

function renderResult(data) {
  if (!data) return;
  $("domain").textContent = data.domain || data.url || "Unknown";
  $("score").textContent = `${data.safety_score}/100`;

  const badge = $("badge");
  badge.className = "status-badge";
  if (data.verdict === "Dangerous") {
    badge.textContent = "Dangerous";
    badge.classList.add("badge-dangerous");
    $("score").style.color = "#ef4444";
  } else if (data.verdict === "Suspicious") {
    badge.textContent = "Suspicious";
    badge.classList.add("badge-suspicious");
    $("score").style.color = "#f59e0b";
  } else {
    badge.textContent = "Safe";
    badge.classList.add("badge-safe");
    $("score").style.color = "#22c55e";
  }

  const threatBox = $("threats");
  if (data.threats && data.threats.length > 0) {
    threatBox.style.display = "block";
    threatBox.innerHTML = `<b>Risk Indicators Detected:</b><br>` + data.threats.map(t => `• ${t}`).join("<br>");
  } else {
    threatBox.style.display = "none";
  }
}

async function analyzeActiveTab() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.url || !tab.url.startsWith("http")) {
      $("domain").textContent = "Non-web page (internal / local)";
      $("badge").textContent = "N/A";
      $("score").textContent = "--";
      return;
    }

    const stored = await chrome.storage.local.get(tab.url);
    if (stored && stored[tab.url]) {
      renderResult(stored[tab.url]);
      return;
    }

    // Fallback: request from backend
    const resp = await fetch(BACKEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: tab.url })
    });
    if (resp.ok) {
      const data = await resp.json();
      renderResult(data);
    }
  } catch (e) {
    $("domain").textContent = "Protection active";
  }
}

$("btn-scan").addEventListener("click", async () => {
  const target = $("custom-url").value.trim();
  if (!target) return;
  $("domain").textContent = "Scanning " + target + "...";
  try {
    const resp = await fetch(BACKEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: target })
    });
    if (resp.ok) {
      const data = await resp.json();
      renderResult(data);
    }
  } catch (e) {
    alert("Could not connect to SelfHeal IT backend.");
  }
});

checkBackend();
analyzeActiveTab();

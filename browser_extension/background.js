/**
 * SelfHeal IT Browser Protection - Background Service Worker
 * Intercepts navigation, queries SelfHeal IT backend or executes local heuristics,
 * updates extension badge color and warning state.
 */

const BACKEND_URL = "http://127.0.0.1:5000/api/browser/check-url";

// Local heuristic fallback if backend is offline
const HIGH_RISK_TLDS = [".xyz", ".top", ".tk", ".ml", ".ga", ".cf", ".gq", ".work", ".click", ".buzz", ".zip", ".mov"];
const PHISH_KEYWORDS = ["verify", "secure", "login", "signin", "account", "update", "billing", "recovery", "banking"];

function localHeuristicCheck(urlString) {
  try {
    const url = new URL(urlString);
    const host = url.hostname.toLowerCase();
    const threats = [];
    let penalty = 0;

    // IP address in host
    if (/^(?:\d{1,3}\.){3}\d{1,3}$/.test(host)) {
      threats.push("Direct IP address used instead of domain name.");
      penalty += 45;
    }
    // Punycode
    if (host.includes("xn--")) {
      threats.push("Disguised homoglyph characters (Punycode xn-- detected).");
      penalty += 40;
    }
    // High risk TLD
    for (const tld of HIGH_RISK_TLDS) {
      if (host.endsWith(tld)) {
        threats.push(`High-risk domain extension: ${tld}`);
        penalty += 25;
        break;
      }
    }
    // Phishing keywords in subdomain
    const subparts = host.split(".");
    if (subparts.length > 2) {
      const sub = subparts.slice(0, -2).join(".");
      for (const kw of PHISH_KEYWORDS) {
        if (sub.includes(kw)) {
          threats.push(`Deceptive keyword '${kw}' in subdomain.`);
          penalty += 35;
          break;
        }
      }
    }

    const score = Math.max(5, 100 - penalty);
    const verdict = score >= 80 ? "Safe" : score >= 50 ? "Suspicious" : "Dangerous";
    return { url: urlString, domain: host, verdict, safety_score: score, threats, source: "local-heuristic" };
  } catch (e) {
    return { url: urlString, domain: "", verdict: "Safe", safety_score: 95, threats: [], source: "fallback" };
  }
}

async function evaluateUrl(url) {
  if (!url || !url.startsWith("http")) return null;
  
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 1200);
    const resp = await fetch(BACKEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    if (resp.ok) {
      const data = await resp.json();
      data.source = "backend-api";
      return data;
    }
  } catch (err) {
    // Backend offline or timeout -> use local heuristic
  }

  return localHeuristicCheck(url);
}

function updateBadge(tabId, result) {
  if (!result) {
    chrome.action.setBadgeText({ tabId, text: "" });
    return;
  }

  if (result.verdict === "Dangerous") {
    chrome.action.setBadgeText({ tabId, text: "!" });
    chrome.action.setBadgeBackgroundColor({ tabId, color: "#e53935" });
  } else if (result.verdict === "Suspicious") {
    chrome.action.setBadgeText({ tabId, text: "?" });
    chrome.action.setBadgeBackgroundColor({ tabId, color: "#fb8c00" });
  } else {
    chrome.action.setBadgeText({ tabId, text: "OK" });
    chrome.action.setBadgeBackgroundColor({ tabId, color: "#43a047" });
  }
}

// Listen to tab updates
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url && tab.url.startsWith("http")) {
    const res = await evaluateUrl(tab.url);
    if (res) {
      updateBadge(tabId, res);
      // Store result in session storage for popup and content script
      chrome.storage.local.set({ [tab.url]: res });
      
      if (res.verdict === "Dangerous") {
        chrome.tabs.sendMessage(tabId, { action: "SHOW_WARNING", result: res }).catch(() => {});
      }
    }
  }
});

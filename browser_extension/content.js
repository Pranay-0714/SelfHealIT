/**
 * SelfHeal IT Browser Protection - In-Page Content Script
 * Injects non-intrusive safety notification banners when a page is flagged as dangerous.
 */

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "SHOW_WARNING" && msg.result) {
    injectWarningBanner(msg.result);
  }
});

// Also check storage on initial page load
(async function init() {
  try {
    const url = window.location.href;
    const stored = await chrome.storage.local.get(url);
    if (stored && stored[url] && stored[url].verdict === "Dangerous") {
      injectWarningBanner(stored[url]);
    }
  } catch (e) {}
})();

function injectWarningBanner(result) {
  if (document.getElementById("selfheal-warning-banner")) return;

  const banner = document.createElement("div");
  banner.id = "selfheal-warning-banner";
  banner.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 2147483647;
    background: #b71c1c;
    color: #ffffff;
    padding: 12px 20px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 14px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.4);
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 2px solid #ff5252;
  `;

  const threatList = (result.threats || []).map(t => `• ${t}`).join(" ");

  banner.innerHTML = `
    <div style="display: flex; align-items: center; gap: 12px;">
      <span style="font-weight: 800; color: #fff; background: rgba(0,0,0,0.3); padding: 4px 8px; border-radius: 4px; font-size: 11px;">ALERT</span>
      <div>
        <strong style="font-weight: 700; letter-spacing: 0.5px;">SelfHeal IT Warning: Potential Phishing / Deceptive Page</strong>
        <div style="font-size: 12px; opacity: 0.9; margin-top: 2px;">
          ${threatList || "This website exhibits indicators of credential harvesting or domain deception."}
        </div>
      </div>
    </div>
    <div style="display: flex; gap: 8px;">
      <button id="selfheal-btn-leave" style="
        background: #ffffff;
        color: #b71c1c;
        border: none;
        padding: 6px 14px;
        border-radius: 4px;
        font-weight: 600;
        cursor: pointer;
        font-size: 13px;
      ">Leave Site</button>
      <button id="selfheal-btn-dismiss" style="
        background: transparent;
        color: #ffffff;
        border: 1px solid rgba(255,255,255,0.4);
        padding: 6px 12px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 13px;
      ">Ignore & Continue</button>
    </div>
  `;

  document.body.prepend(banner);

  document.getElementById("selfheal-btn-leave").addEventListener("click", () => {
    window.location.href = "about:blank";
  });

  document.getElementById("selfheal-btn-dismiss").addEventListener("click", () => {
    banner.remove();
  });
}

# SelfHeal IT — Browser Protection Extension

Real-time browser extension for **Google Chrome**, **Microsoft Edge**, and **Brave** that protects against phishing, deceptive lookalike domains (homoglyphs), and malicious URLs.

---

## Features
- **Heuristic Threat Detection**: Identifies numeric IP hosts, Punycode character disguises, high-risk malicious TLDs (`.xyz`, `.top`, `.tk`), and deceptive brand subdomains (`paypal.verify-account...`).
- **Connected to SelfHeal IT Engine**: Validates browsing activity directly against the local SelfHeal IT diagnostics backend (`http://127.0.0.1:5000/api/browser/check-url`).
- **Offline Fallback Engine**: If the SelfHeal IT backend is stopped, the extension seamlessly switches to built-in local heuristics.
- **In-Page Safety Warning**: Displays an alert banner on flagged malicious pages giving the user one-click options to exit to safety or dismiss.
- **Extension Popup**: Check the active site safety rating, inspect specific risk indicators, or paste any URL into the manual scanner.

---

## Installation Guide

### Microsoft Edge
1. Open Edge and navigate to `edge://extensions`.
2. Toggle **Developer mode** in the left sidebar to **ON**.
3. Click the **Load unpacked** button.
4. Select the `browser_extension` directory inside your SelfHeal IT folder.
5. The **SelfHeal IT Browser Protection** icon will now appear in your toolbar!

### Google Chrome
1. Open Chrome and navigate to `chrome://extensions`.
2. Toggle **Developer mode** in the top-right corner to **ON**.
3. Click the **Load unpacked** button in the top-left corner.
4. Select the `browser_extension` folder.
5. Pin the extension to your toolbar for instant visibility.

---

## Testing Protection
1. Open `http://127.0.0.1:5000` to ensure your SelfHeal IT backend is running.
2. Click the SelfHeal IT extension icon in your browser toolbar.
3. Test a safe URL: enter `https://github.com` in the popup -> rating is **Safe (98/100)**.
4. Test a phishing simulation: enter `http://paypal.verify-security.xyz/login` -> rating is **Dangerous (5/100)** with specific risk indicators flagged.

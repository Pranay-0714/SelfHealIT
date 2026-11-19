"""Browser Protection Subsystem.
Analyzes web URLs for phishing heuristics, homoglyph / Punycode deception,
suspicious top-level domains, IP-based hosts, and credential harvesting patterns.
Used by both the backend API and the Chrome / Edge extension."""
import re, urllib.parse

# Highly trusted root domains that should not trigger false positives
TRUSTED_DOMAINS = {
    "google.com", "microsoft.com", "github.com", "apple.com", "amazon.com",
    "youtube.com", "wikipedia.org", "cloudflare.com", "python.org", "mozilla.org",
    "bing.com", "office.com", "live.com", "linkedin.com", "netflix.com"
}

# TLDs disproportionately used in phishing and disposable throwaway campaigns
HIGH_RISK_TLDS = {
    ".xyz", ".top", ".tk", ".ml", ".ga", ".cf", ".gq", ".work",
    ".click", ".buzz", ".zip", ".mov", ".sbs", ".cam", ".rest"
}

# Suspicious keywords frequently combined into phishing subdomains
PHISHING_KEYWORDS = [
    "verify", "verification", "secure", "login", "signin", "account",
    "update", "billing", "recovery", "support", "authenticate", "banking",
    "confirm", "wallet", "security", "protect", "appleid", "paypal"
]

def analyze_url(url_string):
    """Deep heuristic analysis of a URL.
    Returns:
      verdict: "Safe", "Suspicious", "Dangerous"
      safety_score: 0 to 100
      threats: list of detected heuristic reasons
    """
    if not url_string:
        return {"verdict": "Unknown", "safety_score": 100, "threats": ["Empty URL provided."]}
        
    url = url_string.strip()
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
        
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return {"verdict": "Dangerous", "safety_score": 10, "threats": ["Malformed URL syntax."]}
        
    hostname = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    query = (parsed.query or "").lower()
    
    threats = []
    penalty = 0
    
    # 0. Check trusted whitelist
    for t in TRUSTED_DOMAINS:
        if hostname == t or hostname.endswith("." + t):
            return {
                "url": url_string,
                "domain": hostname,
                "verdict": "Safe",
                "safety_score": 98,
                "threats": [],
                "details": f"Verified trusted domain: {hostname}"
            }
            
    # 1. IP address in hostname (classic phishing / C2 indicator)
    ip_pattern = r"^(?:\d{1,3}\.){3}\d{1,3}$"
    if re.match(ip_pattern, hostname):
        threats.append("Hostname is a direct numeric IP address instead of a domain name.")
        penalty += 45
        
    # 2. Punycode / Internationalized Domain Name (IDN) homoglyph attack
    if "xn--" in hostname:
        threats.append("Uses Punycode (xn--) which may disguise lookalike homoglyph characters.")
        penalty += 40
        
    # 3. Cyrillic / Non-ASCII characters masquerading in URL
    try:
        hostname.encode("ascii")
    except UnicodeEncodeError:
        threats.append("Hostname contains non-ASCII or Cyrillic characters (possible homograph spoof).")
        penalty += 50
        
    # 4. Embedded credentials in URL (e.g. http://user:pass@evil.com)
    if parsed.username or parsed.password:
        threats.append("URL contains embedded HTTP basic authentication credentials.")
        penalty += 40
        
    # 5. Excessive subdomains (e.g. paypal.com.account.verify.evil.com)
    subdomain_parts = hostname.split(".")
    if len(subdomain_parts) >= 4:
        threats.append(f"Excessive subdomain nesting ({len(subdomain_parts)} parts), typical of obfuscated phishing paths.")
        penalty += 25
        
    # 6. Deceptive keywords in subdomains or path combined with untrusted domain
    matched_keywords = [kw for kw in PHISHING_KEYWORDS if kw in hostname]
    if len(matched_keywords) >= 2:
        threats.append(f"Contains multiple deceptive phishing keywords in hostname: {', '.join(matched_keywords)}.")
        penalty += 35
    elif len(matched_keywords) == 1:
        # Check if the keyword is not the main domain
        main_domain = ".".join(subdomain_parts[-2:]) if len(subdomain_parts) >= 2 else hostname
        if matched_keywords[0] in hostname and matched_keywords[0] not in main_domain:
            threats.append(f"Brand/Security keyword '{matched_keywords[0]}' placed deceptively in subdomain.")
            penalty += 30
            
    # 7. High-risk TLD check
    for bad_tld in HIGH_RISK_TLDS:
        if hostname.endswith(bad_tld):
            threats.append(f"Top-level domain '{bad_tld}' has an elevated risk profile for malicious campaigns.")
            penalty += 20
            break
            
    # 8. Unencrypted HTTP login / password submission indicator
    if parsed.scheme == "http" and any(k in path or k in query for k in ("login", "signin", "auth", "token", "password")):
        threats.append("Insecure plain HTTP connection transmitting sensitive authentication keywords.")
        penalty += 25
        
    # Calculate score
    safety_score = max(5, 100 - penalty)
    
    if safety_score >= 80:
        verdict = "Safe"
    elif safety_score >= 50:
        verdict = "Suspicious"
    else:
        verdict = "Dangerous"
        
    return {
        "url": url_string,
        "domain": hostname,
        "verdict": verdict,
        "safety_score": safety_score,
        "threats": threats,
        "details": f"Evaluated {len(threats)} risk indicators." if threats else "No malicious patterns detected."
    }

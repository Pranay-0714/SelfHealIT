import unittest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from selfheal import browser_protection

class TestBrowserProtection(unittest.TestCase):
    def test_safe_trusted_domain(self):
        res = browser_protection.analyze_url("https://github.com/microsoft")
        self.assertEqual(res["verdict"], "Safe")
        self.assertGreaterEqual(res["safety_score"], 80)
        self.assertEqual(len(res["threats"]), 0)

    def test_ip_based_url(self):
        res = browser_protection.analyze_url("http://192.168.1.1/admin-login")
        self.assertEqual(res["verdict"], "Dangerous")
        self.assertTrue(any("ip address" in t.lower() for t in res["threats"]))

    def test_phishing_deceptive_subdomain(self):
        res = browser_protection.analyze_url("http://paypal.account-verify.attacker.xyz/login")
        self.assertEqual(res["verdict"], "Dangerous")
        self.assertTrue(any("phishing keywords" in t.lower() or "deceptive" in t.lower() for t in res["threats"]))

    def test_punycode_homoglyph_detection(self):
        res = browser_protection.analyze_url("http://xn--pypal-4ve.com")
        self.assertTrue(any("punycode" in t.lower() or "homoglyph" in t.lower() for t in res["threats"]))

    def test_high_risk_tld(self):
        res = browser_protection.analyze_url("http://unknown-domain.click")
        self.assertTrue(any(".click" in t for t in res["threats"]))

if __name__ == "__main__":
    unittest.main()

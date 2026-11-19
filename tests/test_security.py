import unittest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from selfheal import security

class TestSecurity(unittest.TestCase):
    def test_defender_status_structure(self):
        status = security.get_defender_status()
        self.assertIsInstance(status, dict)
        self.assertIn("available", status)
        self.assertIn("status", status)

    def test_audit_suspicious_processes(self):
        susp = security.audit_suspicious_processes()
        self.assertIsInstance(susp, list)

    def test_network_ports_audit(self):
        ports = security.audit_network_ports()
        self.assertIsInstance(ports, dict)
        self.assertIn("listening", ports)
        self.assertIn("total_listening", ports)

    def test_defender_scan_unconfirmed_rejected(self):
        res = security.trigger_defender_scan("QuickScan", confirmed=False)
        self.assertFalse(res["ok"])
        self.assertIn("confirmation", res["error"].lower())

    def test_defender_scan_invalid_type(self):
        res = security.trigger_defender_scan("InvalidType", confirmed=True)
        self.assertFalse(res["ok"])
        self.assertIn("invalid", res["error"].lower())

if __name__ == "__main__":
    unittest.main()

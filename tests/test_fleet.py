import unittest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from selfheal import fleet, config

class TestFleet(unittest.TestCase):
    def setUp(self):
        self.cfg = config.load_config()
        self.token = self.cfg.get("agent_secret_key", "selfheal-agent-default-secret-token-key")

    def test_authentication_valid(self):
        self.assertTrue(fleet.authenticate_agent(f"Bearer {self.token}"))
        self.assertTrue(fleet.authenticate_agent(self.token))

    def test_authentication_invalid(self):
        self.assertFalse(fleet.authenticate_agent("Bearer invalid_token_123"))
        self.assertFalse(fleet.authenticate_agent(""))
        self.assertFalse(fleet.authenticate_agent(None))

    def test_record_heartbeat(self):
        mock_data = {
            "hostname": "Test-Client-Node-01",
            "cpu_percent": 15.0,
            "ram_percent": 42.0,
            "ram_total_gb": 16.0,
            "health_score": 98,
            "disks": [{"mount": "C:\\", "percent": 40}]
        }
        rec = fleet.record_heartbeat(mock_data, "192.168.1.150")
        self.assertEqual(rec["hostname"], "Test-Client-Node-01")
        self.assertEqual(rec["remote_ip"], "192.168.1.150")

        summary = fleet.get_fleet_summary()
        self.assertGreater(len(summary), 0)
        found = any(n["hostname"] == "Test-Client-Node-01" for n in summary)
        self.assertTrue(found)

    def test_remove_agent(self):
        fleet.record_heartbeat({"hostname": "Temporary-Node"}, "127.0.0.1")
        self.assertTrue(fleet.remove_agent("Temporary-Node"))
        self.assertFalse(fleet.remove_agent("NonExistentHost"))

if __name__ == "__main__":
    unittest.main()

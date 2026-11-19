import unittest, sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import app
from selfheal import config

class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.cfg = config.load_config()
        cls.token = cls.cfg.get("agent_secret_key", "selfheal-agent-default-secret-token-key")

    def test_dashboard_index(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"SelfHeal IT", r.data)

    def test_api_scan(self):
        r = self.client.post("/api/scan")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn("health_score", d)
        self.assertIn("cpu", d)

    def test_api_scan_latest(self):
        r = self.client.get("/api/scan/latest")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn("cpu", d)

    def test_api_chat(self):
        r = self.client.post("/api/chat", json={"question": "how is my ram?"})
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn("answer", d)

    def test_api_chat_compatibility(self):
        r = self.client.post("/api/chat/compatibility", json={"title": "valorant"})
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertTrue(d.get("ok"))

    def test_api_chat_bottlenecks(self):
        r = self.client.get("/api/chat/bottlenecks")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn("bottlenecks", d)

    def test_api_monitoring_stats(self):
        r = self.client.get("/api/monitoring/stats")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn("cpu_percent", d)
        self.assertIn("ram_percent", d)

    def test_api_monitoring_history(self):
        r = self.client.get("/api/monitoring/history")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn("cpu", d)

    def test_api_heal_actions(self):
        r = self.client.get("/api/heal/actions")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIsInstance(d, list)

    def test_api_heal_execute_unconfirmed(self):
        r = self.client.post("/api/heal", json={"action": "clean_temp", "confirmed": False})
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertFalse(d["ok"])

    def test_api_security_status(self):
        r = self.client.get("/api/security/status")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn("defender", d)
        self.assertIn("ports", d)

    def test_api_browser_check(self):
        r = self.client.post("/api/browser/check-url", json={"url": "https://google.com"})
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertEqual(d["verdict"], "Safe")

    def test_api_agent_report_authorized(self):
        payload = {
            "hostname": "Fleet-Client-99",
            "cpu_percent": 22.0,
            "ram_percent": 55.0,
            "health_score": 90
        }
        r = self.client.post("/api/agent/report", json=payload,
                             headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertTrue(d["ok"])

    def test_api_agent_report_unauthorized(self):
        payload = {"hostname": "Hacker-PC"}
        r = self.client.post("/api/agent/report", json=payload,
                             headers={"Authorization": "Bearer bad-token"})
        self.assertEqual(r.status_code, 401)

    def test_api_agent_fleet(self):
        r = self.client.get("/api/agent/fleet")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIsInstance(d, list)

    def test_api_export_pdf(self):
        r = self.client.get("/api/export/pdf")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.mimetype, "application/pdf")
        self.assertTrue(r.data.startswith(b"%PDF"))

    def test_api_export_json(self):
        r = self.client.get("/api/export/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.mimetype, "application/json")

    def test_api_settings_get_post(self):
        r_get = self.client.get("/api/settings")
        self.assertEqual(r_get.status_code, 200)
        
        r_post = self.client.post("/api/settings", json={"cpu_alert_threshold": 92})
        self.assertEqual(r_post.status_code, 200)

if __name__ == "__main__":
    unittest.main()

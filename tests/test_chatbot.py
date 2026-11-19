import unittest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from selfheal import chatbot

class TestChatbot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_scan = {
            "timestamp": "2026-01-01T00:00:00",
            "os": {"system": "Windows", "release": "11", "uptime_hours": 12.0},
            "cpu": {"name": "Intel Core i5", "physical_cores": 4, "logical_cores": 8, "usage_percent": 35.0},
            "ram": {"total_gb": 16.0, "available_gb": 8.0, "percent": 50.0, "swap_percent": 10.0},
            "gpu": "NVIDIA GeForce RTX 3060 (12 GB VRAM)",
            "gpus": [{"name": "NVIDIA GeForce RTX 3060", "memory_gb": 12.0, "driver": "550.0"}],
            "disks": [{"mount": "C:\\", "total_gb": 500.0, "free_gb": 250.0, "percent": 50.0}],
            "top_processes": [{"name": "chrome.exe", "mem_percent": 3.0, "cpu_percent": 1.0}],
            "wifi": {"SSID": "HomeMesh", "Signal": "95%"},
            "network": {"total": 10, "established": 5, "listening": 5},
            "suspicious": [],
            "hung_apps": [],
            "findings": [],
            "health_score": 95
        }

    def test_compatibility_known_game(self):
        res = chatbot.check_compatibility("valorant", self.mock_scan)
        self.assertTrue(res["ok"])
        self.assertTrue(res["found"])
        self.assertIn("Exceeds Recommended", res["verdict"])

    def test_compatibility_workstation_software(self):
        res = chatbot.check_compatibility("blender", self.mock_scan)
        self.assertTrue(res["ok"])
        self.assertIn("Blender", res["title"])

    def test_compatibility_unknown_no_hallucination(self):
        res = chatbot.check_compatibility("completely_fake_game_xyz", self.mock_scan)
        self.assertFalse(res["found"])
        self.assertIn("won't guess", res["message"])

    def test_bottleneck_analysis(self):
        ans = chatbot.analyze_bottlenecks(self.mock_scan)
        self.assertIsInstance(ans, str)
        self.assertIn("Bottleneck", ans)

    def test_rule_based_questions(self):
        ans_ram = chatbot.rule_based("how is my ram?", self.mock_scan)
        self.assertIn("16.0 GB", ans_ram)

        ans_cpu = chatbot.rule_based("why is my cpu?", self.mock_scan)
        self.assertIn("Intel Core i5", ans_cpu)

        ans_disk = chatbot.rule_based("storage space", self.mock_scan)
        self.assertIn("C:\\", ans_disk)

        ans_wifi = chatbot.rule_based("what is my wifi network?", self.mock_scan)
        self.assertIn("HomeMesh", ans_wifi)

    def test_unscanned_system(self):
        ans = chatbot.rule_based("how much ram?", None)
        self.assertIn("Run a scan first", ans)

if __name__ == "__main__":
    unittest.main()

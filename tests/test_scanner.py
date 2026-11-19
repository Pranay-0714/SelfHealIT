import unittest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from selfheal import scanner

class TestScanner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scan = scanner.scan()

    def test_scan_structure(self):
        required_keys = ["timestamp", "os", "cpu", "ram", "gpu", "disks", "network", "findings", "health_score"]
        for k in required_keys:
            self.assertIn(k, self.scan)

    def test_health_score_range(self):
        score = self.scan["health_score"]
        self.assertIsInstance(score, int)
        self.assertTrue(0 <= score <= 100)

    def test_cpu_metrics(self):
        cpu = self.scan["cpu"]
        self.assertGreater(cpu["logical_cores"], 0)
        self.assertTrue(0 <= cpu["usage_percent"] <= 100)

    def test_ram_metrics(self):
        ram = self.scan["ram"]
        self.assertGreater(ram["total_gb"], 0)
        self.assertTrue(0 <= ram["percent"] <= 100)
        self.assertIn("swap", ram)

    def test_swap_safe_no_crash(self):
        sw = scanner.get_swap_safe()
        self.assertIn("total_gb", sw)
        self.assertIn("percent", sw)

    def test_gpu_retrieval(self):
        gpus = scanner.get_gpu_details()
        self.assertIsInstance(gpus, list)
        self.assertGreater(len(gpus), 0)
        self.assertIn("name", gpus[0])

    def test_hung_apps_type(self):
        hung = scanner.get_hung_applications()
        self.assertIsInstance(hung, list)

    def test_findings_analysis(self):
        mock_data = {
            "cpu": {"usage_percent": 95, "logical_cores": 4, "physical_cores": 2},
            "ram": {"percent": 92, "total_gb": 8, "available_gb": 0.5},
            "disks": [{"mount": "C:\\", "percent": 98, "free_gb": 1.2}],
            "os": {"uptime_hours": 400},
            "startup_apps": [{"name": f"app_{i}"} for i in range(15)],
            "suspicious": [{"name": "fake.exe", "pid": 9999, "reason": "test"}],
            "defender": {"available": True, "realtime_enabled": False},
            "hung_apps": [{"name": "frozen.exe", "pid": 8888, "reason": "hung"}]
        }
        findings = scanner.analyze(mock_data)
        self.assertGreaterEqual(len(findings), 6)
        problems = [f["problem"].lower() for f in findings]
        self.assertTrue(any("cpu" in p for p in problems))
        self.assertTrue(any("memory" in p for p in problems))
        self.assertTrue(any("disk" in p for p in problems))
        self.assertTrue(any("defender" in p for p in problems))
        self.assertTrue(any("unresponsive" in p for p in problems))

if __name__ == "__main__":
    unittest.main()

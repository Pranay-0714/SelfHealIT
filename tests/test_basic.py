import unittest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from selfheal import scanner, chatbot, loopdemo, reports, healing
from app import app

class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.scan = scanner.scan()
    def test_scan_keys(self):
        for k in ("cpu", "ram", "disks", "findings", "os"): self.assertIn(k, self.scan)
    def test_chat_ram(self): self.assertIn("RAM", chatbot.rule_based("how much ram?", self.scan))
    def test_chat_game(self): self.assertIn("minecraft", chatbot.rule_based("can I run minecraft", self.scan).lower())
    def test_unknown_game_no_invention(self):
        self.assertIn("won't guess", chatbot.rule_based("can I run zzzgame", self.scan))
    def test_no_scan(self): self.assertIn("Run a scan", chatbot.rule_based("hi", None))
    def test_pdf(self): self.assertTrue(reports.to_pdf(self.scan).startswith(b"%PDF"))
    def test_heal_needs_confirm(self): self.assertFalse(healing.run_action("clean_temp", False)["ok"])
    def test_heal_rejects_unknown(self): self.assertFalse(healing.run_action("rm -rf /", True)["ok"])
    def test_loop_demo(self):
        r = loopdemo.run_demo(timeout=4); self.assertTrue(r["ok"]); self.assertEqual(len(r["steps"]), 4)
    def test_api(self):
        c = app.test_client()
        self.assertEqual(c.get("/").status_code, 200)
        self.assertEqual(c.post("/api/scan").status_code, 200)
        self.assertEqual(c.get("/api/export/pdf").status_code, 200)
        self.assertEqual(c.post("/api/chat", json={"question": "cpu?"}).status_code, 200)

if __name__ == "__main__": unittest.main()

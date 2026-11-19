import unittest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from selfheal import healing

class TestHealing(unittest.TestCase):
    def test_list_actions(self):
        actions = healing.list_actions()
        self.assertIsInstance(actions, list)
        self.assertGreaterEqual(len(actions), 5)
        ids = [a["id"] for a in actions]
        self.assertIn("clean_temp", ids)
        self.assertIn("flush_dns", ids)
        self.assertIn("empty_recycle_bin", ids)

    def test_rejection_without_confirmation(self):
        res = healing.run_action("clean_temp", False)
        self.assertFalse(res["ok"])
        self.assertIn("confirmation required", res["error"].lower())

    def test_rejection_unknown_action(self):
        res = healing.run_action("malicious_command_or_script", True)
        self.assertFalse(res["ok"])
        self.assertIn("unknown action", res["error"].lower())

    def test_protected_process_termination(self):
        # Attempting to terminate protected process like 'svchost' or 'explorer' must be rejected
        res = healing.run_action("restart_unresponsive_app", True, target_pid=0) # PID 0 is System Idle
        self.assertFalse(res["verified"])

    def test_clean_temp_execution(self):
        res = healing.run_action("clean_temp", True)
        self.assertTrue(res["ok"])
        self.assertIn("freed_mb", res)
        self.assertTrue(res["verified"])

    def test_activity_logging(self):
        healing.log("test_audit_event", detail="unit test log")
        logs = healing.get_activity_logs(10)
        self.assertIsInstance(logs, list)
        self.assertGreater(len(logs), 0)
        events = [l.get("event") for l in logs]
        self.assertIn("test_audit_event", events)

if __name__ == "__main__":
    unittest.main()

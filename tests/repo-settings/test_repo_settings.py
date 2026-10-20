import importlib.util
import pathlib
import unittest

spec = importlib.util.spec_from_file_location(
    "rs", pathlib.Path(__file__).parents[2] / "tools/repo-settings/repo_settings.py")
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)


class T(unittest.TestCase):
    def test_no_checks_rule_when_none_ran(self):
        rules = rs.desired([])["protect-main"]["rules"]
        self.assertNotIn("required_status_checks", {r["type"] for r in rules})

    def test_satisfies_with_extra(self):
        want = rs.desired(["gate"])["protect-main"]
        cur = rs.merge_up({"rules": [{"type": "required_linear_history"}], "bypass_actors": []}, want)
        cur["enforcement"] = "active"
        self.assertTrue(rs.satisfies(cur, want))

    def test_merge_up_keeps_contexts(self):
        want = rs.desired(["gate"])["protect-main"]
        cur = rs.desired(["gate", "extra"])["protect-main"]
        self.assertEqual(rs.contexts(rs.merge_up(cur, want)["rules"]), {"gate", "extra"})

    def test_missing_type_fails(self):
        want = rs.desired(["gate"])["protect-main"]
        cur = rs.desired([])["protect-main"]
        self.assertFalse(rs.satisfies(cur, want))


if __name__ == "__main__":
    unittest.main()

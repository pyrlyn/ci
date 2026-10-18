import importlib.util, os, tempfile, unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("sd", Path(__file__).parents[2] / "tools/sync-docs/sync_docs.py")
sd = importlib.util.module_from_spec(spec); spec.loader.exec_module(sd)


class Mirror(unittest.TestCase):
    def test_filters_and_delete(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t); src, dest = t / "s", t / "d"
            for f in ["a.md", "guide/b.md", "research/x.md", "plan-1.md", "site.md", "ru/c.md", "compat.md", "img.png"]:
                (src / f).parent.mkdir(parents=True, exist_ok=True); (src / f).write_text("x")
            (dest / "stale.md").parent.mkdir(parents=True); (dest / "stale.md").write_text("x")
            (dest / "ru").mkdir(); (dest / "ru/keep.md").write_text("x")
            sd.mirror(src, dest, sd.INTERNAL + ["compat.md", "/ru/"], {"ru"})
            got = sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file())
            self.assertEqual(got, ["a.md", "guide/b.md", "ru/keep.md"])

    def test_internal_names_case_insensitive(self):
        for name in ["PLAN.md", "Plan.md", "README.md", "TODO-2.md", "AGENTS.md"]:
            self.assertTrue(sd.excluded(name, False, sd.INTERNAL), name)
        self.assertFalse(sd.excluded("agents.md", False, sd.INTERNAL))

    def test_version(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "site.md"; p.write_text('---\ntitle: x\nversion: "0.1"\n---\nbody\n')
            sd.set_version(p, "1.2.3")
            self.assertIn('version: "1.2.3"', p.read_text())


if __name__ == "__main__":
    unittest.main()

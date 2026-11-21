import unittest
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from selector import optimizer_fixture_only, schedule


class SelectorTests(unittest.TestCase):
    def test_schedule_uses_overhead(self):
        self.assertEqual(len(schedule([{"seconds": 0.1, "number": i} for i in range(10)])), 1)
        plan = schedule([{"seconds": 10, "number": i} for i in range(4)])
        self.assertEqual(len(plan), 4)
        self.assertEqual(sorted(n for w in plan for n in w), list(range(4)))

    def test_fixture_only_and_fallback(self):
        a = b"tests/fixtures/optimizer/example.sql"
        b = b"sqlglot/optimizer/optimizer.py"

        def patch(f):
            return b"diff --git a/" + f + b" b/" + f + b"\n--- a/" + f + b"\n+++ b/" + f

        self.assertTrue(optimizer_fixture_only(patch(a), {a}))
        self.assertFalse(optimizer_fixture_only(patch(a) + b"\n" + patch(b), {a}))
        self.assertFalse(optimizer_fixture_only(patch(a), set()))
        self.assertFalse(optimizer_fixture_only(patch(a).split(b"\n")[0], {a}))
        self.assertFalse(optimizer_fixture_only(b"", {a}))

    def test_local_batch_routes_on_static_ownership(self):
        script = Path(__file__).with_name("selector.py")
        ownership = json.loads(script.with_name("optimizer_fixtures.json").read_text())
        (first, a), (second, b) = [(p, owners) for p, owners in ownership.items() if owners][:2]
        ids = sorted(set(a + b))
        extra = "tests/test_optimizer.py::TestOptimizer::test_unrelated"
        outside = "tests/test_other.py::TestOther::test_unrelated"
        catalog = [{"id": n, "file": n.split("::")[0], "seconds": 0.01, "number": i}
                   for i, n in enumerate([*ids, extra, outside])]
        def patch(p):
            return f"diff --git a/{p} b/{p}\n--- a/{p}\n+++ b/{p}\n@@ -1 +1 @@\n-SELECT 1;\n+SELECT 2;\n"
        with TemporaryDirectory() as tmp:
            data = Path(tmp)
            patch_dir = data / "commits"
            patch_dir.mkdir()
            (data / "tests.json").write_text(json.dumps({"tests": catalog}))
            (patch_dir / "owned.patch").write_text(patch(first))
            (patch_dir / "two.patch").write_text(patch(first) + patch(second))
            (patch_dir / "mixed.patch").write_text(patch(first) + patch("sqlglot/unknown.py"))
            answer = subprocess.check_output([sys.executable, script, "--data", data], text=True)
            observed = {j["commit"]: {catalog[n]["id"] for w in j["workers"] for n in w}
                        for j in map(json.loads, answer.splitlines())}
            self.assertEqual(observed, {"owned": set(a), "two": set(ids), "mixed": {*ids, extra, outside}})



if __name__ == "__main__":
    unittest.main()

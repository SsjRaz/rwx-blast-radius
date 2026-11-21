import unittest
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


if __name__ == "__main__":
    unittest.main()

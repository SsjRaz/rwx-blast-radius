"""Conservative CI selector for independently applied sqlglot patches."""
import argparse
import heapq
import json
import re
from pathlib import Path


def schedule(tests):
    if not tests:
        return []
    pairs = sorted(((round(t["seconds"] * 1000), t["number"]) for t in tests), reverse=True)
    want = float("inf")
    plan = []
    total = sum(ms for ms, _ in pairs)
    for k in range(1, min(8, len(pairs)) + 1):
        if max(pairs[0][0], (total + k - 1) // k) + k * 2000 >= want:
            continue
        heap = [(0, i) for i in range(k)]
        workers = [[] for _ in range(k)]
        for ms, n in pairs:
            load, i = heapq.heappop(heap)
            workers[i].append(n)
            heapq.heappush(heap, (load + ms, i))
        workers = [w for w in workers if w]
        score = max(load for load, _ in heap) + 2000 * len(workers)
        if score < want:
            plan, want = workers, score
    return plan


# A unified diff may contain multiple files. Reject ambiguous/quoted/rename
# headers rather than guessing. Only the audited direct fixture directory
# has a narrow consumer; unknown or mixed changes fall back to the full suite.
HEADER = re.compile(rb"diff --git a/([A-Za-z0-9_./-]+) b/([A-Za-z0-9_./-]+)")
OPTIMIZER_TEST = "tests/test_optimizer.py"


def fixture_paths(data, known_paths):
    found = set()
    current = None
    old_path = new_path = False
    for line in data.splitlines():
        if line.startswith(b"diff "):
            if found and not (old_path and new_path):
                return False
            m = HEADER.fullmatch(line)
            if not m or m[1] != m[2] or m[1] not in known_paths:
                return False
            current = m[1]
            old_path = new_path = False
            found.add(current)
        elif line.startswith(b"--- "):
            if current is None or line != b"--- a/" + current or old_path:
                return False
            old_path = True
        elif line.startswith(b"+++ "):
            if current is None or line != b"+++ b/" + current or new_path:
                return False
            new_path = True
    return found if old_path and new_path else set()


def optimizer_fixture_only(data, known_paths):
    return bool(fixture_paths(data, known_paths))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("/data"))
    args = ap.parse_args()
    tests = json.loads((args.data / "tests.json").read_text())["tests"]
    full_plan = json.dumps(schedule(tests), separators=(",", ":"))
    optimizer = [test for test in tests if test["file"] == OPTIMIZER_TEST]
    optimizer_plan = json.dumps(schedule(optimizer), separators=(",", ":")) if optimizer else full_plan
    paths = json.loads(Path(__file__).with_name("optimizer_fixtures.json").read_text())
    known = {path.encode("ascii"): set(ids) for path, ids in paths.items()}
    by_id = {test["id"]: test for test in tests}
    for patch in sorted((args.data / "commits").glob("*.patch")):
        touched = fixture_paths(patch.read_bytes(), known)
        plan = full_plan
        if touched:
            candidates = [known[path] for path in touched]
            # Use the module fallback if any fixture lacks a proven direct
            # consumer or the catalog does not have the expected ID.
            if all(ids and ids <= by_id.keys() for ids in candidates):
                selected = set().union(*candidates)
                plan = json.dumps(schedule(by_id[i] for i in selected), separators=(",", ":"))
            else:
                plan = optimizer_plan
        print('{"commit":' + json.dumps(patch.stem) + ',"workers":' + plan + '}')


if __name__ == "__main__":
    main()

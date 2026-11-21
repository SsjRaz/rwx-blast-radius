# RWX Blast Radius: conservative CI test selection

The selector reads the supplied test catalog and unified diffs. It never
executes patch content. It prints one JSON line per commit, with test IDs assigned
to at most eight workers. No sample data or answers are required at runtime.

## Selection policy

Code, unknown paths, unusual patch headers and mixed changes use the full
suite. A patch confined to existing top-level optimizer SQL fixtures uses
the union of their direct consumers in `tests/test_optimizer.py` where each
consumer is established in the organizer's pinned source and present in the
test catalog. If a known fixture has no mapped consumer or its consumer is
missing from the catalog, the selector runs the optimizer test module (or
the full suite if that module is missing).

`generate_fixture_map.py` builds the map from literal arguments to the
pinned module's fixture-loader calls at sqlglot revision
`eb11aec4be8cb2122afe713a4816662c3f0fb2fa`. It does not use sample patches,
answers, scores, or observed outcomes. Regenerate the checked-in map with:

```sh
python3 generate_fixture_map.py /path/to/sqlglot-git-checkout > optimizer_fixtures.json
```

Static ownership is not a formal guarantee of hidden-case recall.

For each selection set, test durations are converted to the scorer's integer
milliseconds. Longest-first placement balances worker loads. The selector
tries varying worker counts from one through eight, rejects counts whose
lower bound cannot beat the incumbent, and keeps the cheapest discovered
plan under the scorer's 2s-per-worker overhead.

## Reproduce

The image startup command uses `/data` and makes no filesystem writes. To
exercise the same selector with an organizer sample unpacked somewhere else:

```sh
python3 selector.py --data /path/to/sample > output.jsonl
python3 /path/to/score.py /path/to/sample /path/to/sample/answers.json output.jsonl
```

Build the root Dockerfile for linux/amd64, then use the organizer's documented
run limits and read-only mounts. The supplied image recipe has not been
locally run where Docker is unavailable.

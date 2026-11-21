"""Regenerate direct optimizer fixture dependencies from the pinned tree."""
import argparse
import ast
from collections import defaultdict
import json
from pathlib import Path
import subprocess

PIN = "eb11aec4be8cb2122afe713a4816662c3f0fb2fa"
TEST = "tests/test_optimizer.py"
ROOT = "tests/fixtures/optimizer/"


def generate(root):
    def tracked(*args):
        return subprocess.check_output(["git", "-C", root, *args], text=True)

    tree = ast.parse(tracked("show", f"{PIN}:{TEST}"))
    paths = {p for p in tracked("ls-tree", "-r", "--name-only", PIN, ROOT).splitlines()
             if p.endswith(".sql") and "/" not in p.removeprefix(ROOT)}
    owners = defaultdict(set)
    for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
        for fn in (node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")):
            for call in (node for node in ast.walk(fn) if isinstance(node, ast.Call)):
                target = call.func
                if isinstance(target, ast.Attribute) and target.attr == "check_file":
                    arg = call.args[0]
                    if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
                        raise ValueError("dynamic check_file not supported")
                    path = ROOT + arg.value + ".sql"
                elif isinstance(target, ast.Name) and target.id in {"load_sql_fixtures", "load_sql_fixture_pairs"}:
                    arg = call.args[0]
                    if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
                        raise ValueError("dynamic fixture loader not supported")
                    path = "tests/fixtures/" + arg.value
                else:
                    continue
                if path in paths:
                    owners[path].add(f"{TEST}::{cls.name}::{fn.name}")
    return {p: sorted(owners[p]) for p in sorted(paths)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pinned_repo", type=Path)
    args = parser.parse_args()
    print(json.dumps(generate(args.pinned_repo), indent=2))

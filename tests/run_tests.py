#!/usr/bin/env python3
"""Cross-test runner for tests/hp12c-reference.json.

Feeds each case's key sequence into a fresh Engine and prints an
EXPECTED / ACTUAL / MATCH line per case, per the project's benchmark
requirement. Exits non-zero if any case fails.

Usage: python tests/run_tests.py [path-to-json]
"""
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from hp12c.engine import Engine  # noqa: E402


def run_case(case: dict) -> tuple[bool, str]:
    engine = Engine()
    if "setup_capacity" in case:
        engine.mem.ensure_capacity(case["setup_capacity"])
    for key in case["keys"]:
        engine.press(key)

    expect = case["expect"]
    checks = []

    if "error" in expect:
        actual_code = engine.error.code if engine.error else None
        checks.append(("error", expect["error"], actual_code, actual_code == expect["error"]))
    if "x" in expect:
        actual = engine.stack.x
        expected = Decimal(expect["x"])
        checks.append(("x", str(expected), str(actual), actual == expected))
    if "y" in expect:
        actual = engine.stack.y
        expected = Decimal(expect["y"])
        checks.append(("y", str(expected), str(actual), actual == expected))
    if "z" in expect:
        actual = engine.stack.z
        expected = Decimal(expect["z"])
        checks.append(("z", str(expected), str(actual), actual == expected))
    if "begin" in expect:
        actual = engine.mem.financial.begin
        checks.append(("begin", expect["begin"], actual, actual == expect["begin"]))
    if "t" in expect:
        actual = engine.stack.t
        expected = Decimal(expect["t"])
        checks.append(("t", str(expected), str(actual), actual == expected))
    if "display" in expect:
        actual = engine.display_text()
        checks.append(("display", expect["display"], actual, actual == expect["display"]))
    if "program_capacity" in expect:
        actual = engine.mem.program_capacity
        checks.append(("program_capacity", expect["program_capacity"], actual, actual == expect["program_capacity"]))
    if "converted_count" in expect:
        actual = engine.mem.converted_count
        checks.append(("converted_count", expect["converted_count"], actual, actual == expect["converted_count"]))

    all_pass = all(c[3] for c in checks)
    detail_lines = [f"    {name}: expected={exp!r} actual={act!r} {'MATCH' if ok else 'MISMATCH'}"
                     for name, exp, act, ok in checks]
    return all_pass, "\n".join(detail_lines)


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "tests" / "hp12c-reference.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    passed = 0
    failed = 0
    by_category: dict[str, list[bool]] = {}

    for case in data["cases"]:
        try:
            ok, detail = run_case(case)
        except Exception as exc:  # noqa: BLE001
            ok, detail = False, f"    EXCEPTION: {exc!r}"
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case['id']} - {case['description']}")
        print(detail)
        by_category.setdefault(case["category"], []).append(ok)
        passed += ok
        failed += not ok

    print("\n" + "=" * 60)
    print("Summary by category:")
    for cat, results in sorted(by_category.items()):
        p = sum(results)
        print(f"  {cat}: {p}/{len(results)} passed")
    print(f"\nTOTAL: {passed} passed, {failed} failed, {passed + failed} cases")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

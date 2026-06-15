"""
Eval runner — calls the live /agent/respond endpoint and checks each eval case.

Usage:
    python evals/run_evals.py [--base-url http://localhost:8000] [--verbose]

Checks per eval case:
  - expected_agent matches selected_agent
  - all expected_tools appear in tools_used
  - all must_include terms appear in the answer
  - no must_not_include terms appear in the answer
  - safety_behavior is respected (block/escalate cases)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

EVALS_FILE = Path(__file__).parent / "eval_cases.json"
PASS = "✓ PASS"
FAIL = "✗ FAIL"


def check_case(case: dict, response: dict) -> tuple[bool, list[str]]:
    failures: list[str] = []

    answer = response.get("answer", "").lower()
    selected_agent = response.get("selected_agent", "")
    tools_used = response.get("tools_used", [])
    guardrail = response.get("guardrail_result", {})

    # Check expected_agent
    if case.get("expected_agent") and selected_agent != case["expected_agent"]:
        failures.append(
            f"Agent mismatch: expected '{case['expected_agent']}', got '{selected_agent}'"
        )

    # Check expected_tools (all must appear)
    for tool in case.get("expected_tools", []):
        if tool not in tools_used:
            failures.append(f"Missing tool: '{tool}' not in {tools_used}")

    # Check must_include terms
    for term in case.get("must_include", []):
        if term.lower() not in answer:
            failures.append(f"Missing term in answer: '{term}'")

    # Check must_not_include terms
    for term in case.get("must_not_include", []):
        if term.lower() in answer:
            failures.append(f"Forbidden term in answer: '{term}'")

    # Check safety_behavior
    safety = case.get("safety_behavior")
    if safety in ("block", "escalate", "escalate_or_block"):
        if not guardrail.get("guardrail_triggered") and selected_agent not in (
            "HumanHandoffAgent",
        ):
            failures.append(
                f"Safety behavior '{safety}' expected but not triggered. "
                f"Agent: {selected_agent}, guardrail: {guardrail}"
            )

    if safety == "graceful_not_found":
        # Should not crash — just check response arrived
        if not answer:
            failures.append("Empty answer for graceful_not_found case")

    return len(failures) == 0, failures


async def run_all(base_url: str, verbose: bool) -> None:
    cases: list[dict] = json.loads(EVALS_FILE.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []

    print(f"\nRunning {len(cases)} eval cases against {base_url}\n")
    print(f"{'ID':<12} {'Description':<45} {'Result':<10} {'Latency'}")
    print("-" * 90)

    async with httpx.AsyncClient(base_url=base_url, timeout=120.0) as client:
        for case in cases:
            start = time.perf_counter()
            try:
                resp = await client.post("/agent/respond", json=case["input"])
                resp.raise_for_status()
                data = resp.json()
                passed, failures = check_case(case, data)
            except Exception as exc:
                passed = False
                failures = [f"HTTP error: {exc}"]
                data = {}

            latency = round((time.perf_counter() - start) * 1000)
            status = PASS if passed else FAIL

            print(
                f"{case['id']:<12} {case['description'][:44]:<45} {status:<10} {latency}ms"
            )

            if verbose and not passed:
                for f in failures:
                    print(f"           → {f}")

            results.append({
                "id": case["id"],
                "passed": passed,
                "failures": failures,
                "latency_ms": latency,
                "selected_agent": data.get("selected_agent"),
                "tools_used": data.get("tools_used", []),
            })

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    print("-" * 90)
    print(f"\nResults: {passed_count}/{total} passed ({round(passed_count/total*100)}%)\n")

    if passed_count < total:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run streaming-support-agent evals")
    parser.add_argument(
        "--base-url", default="http://localhost:8000", help="Base URL of the running API"
    )
    parser.add_argument("--verbose", action="store_true", help="Show failure details")
    args = parser.parse_args()

    asyncio.run(run_all(args.base_url, args.verbose))

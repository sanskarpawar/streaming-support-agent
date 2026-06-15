"""
Eval runner — calls the live /agent/respond endpoint and checks each eval case.

Usage:
    python evals/run_evals.py [--base-url http://localhost:8000] [--verbose] [--output evals/reports]

Checks per eval case:
  - expected_agent matches selected_agent
  - all expected_tools appear in tools_used
  - all must_include terms appear in the answer
  - no must_not_include terms appear in the answer
  - safety_behavior is respected (block/escalate cases)

Reports are saved to <output>/<timestamp>_report.{json,md} automatically.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

EVALS_FILE = Path(__file__).parent / "eval_cases.json"
REPORTS_DIR = Path(__file__).parent / "reports"
PASS = "PASS"
FAIL = "FAIL"


def check_case(case: dict, response: dict) -> tuple[bool, list[str]]:
    failures: list[str] = []

    answer = response.get("answer", "").lower()
    selected_agent = response.get("selected_agent", "")
    tools_used = response.get("tools_used", [])
    guardrail = response.get("guardrail_result", {})

    if case.get("expected_agent") and selected_agent != case["expected_agent"]:
        failures.append(
            f"Agent mismatch: expected '{case['expected_agent']}', got '{selected_agent}'"
        )

    for tool in case.get("expected_tools", []):
        # SK prefixes tools as "{PluginName}-{function_name}".
        # Accept both the bare name and any plugin-prefixed variant.
        tool_found = tool in tools_used or any(
            t == tool or t.endswith(f"-{tool}") for t in tools_used
        )
        if not tool_found:
            failures.append(f"Missing tool: '{tool}' not in {tools_used}")

    for term in case.get("must_include", []):
        if term.lower() not in answer:
            failures.append(f"Missing term in answer: '{term}'")

    for term in case.get("must_not_include", []):
        if term.lower() in answer:
            failures.append(f"Forbidden term in answer: '{term}'")

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
        if not answer:
            failures.append("Empty answer for graceful_not_found case")

    return len(failures) == 0, failures


def save_json_report(
    results: list[dict],
    cases: list[dict],
    passed_count: int,
    base_url: str,
    elapsed_s: float,
    output_dir: Path,
    timestamp: str,
) -> Path:
    report = {
        "timestamp": timestamp,
        "base_url": base_url,
        "total": len(results),
        "passed": passed_count,
        "failed": len(results) - passed_count,
        "pass_rate_pct": round(passed_count / len(results) * 100, 1),
        "total_elapsed_s": round(elapsed_s, 2),
        "cases": results,
    }
    path = output_dir / f"{timestamp}_report.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def save_markdown_report(
    results: list[dict],
    cases: list[dict],
    passed_count: int,
    base_url: str,
    elapsed_s: float,
    output_dir: Path,
    timestamp: str,
) -> Path:
    total = len(results)
    lines: list[str] = [
        "# Eval Report — Streaming Support Agent",
        "",
        f"**Date:** {timestamp.replace('_', ' ')}  ",
        f"**API:** {base_url}  ",
        f"**Result:** {passed_count}/{total} passed ({round(passed_count/total*100)}%)  ",
        f"**Total time:** {round(elapsed_s, 2)}s",
        "",
        "---",
        "",
        "## Results",
        "",
        "| ID | Description | Agent | Tools Used | Result | Latency |",
        "|---|---|---|---|---|---|",
    ]

    case_map = {c["id"]: c for c in cases}
    for r in results:
        case = case_map.get(r["id"], {})
        icon = "✅" if r["passed"] else "❌"
        tools = ", ".join(r.get("tools_used") or []) or "—"
        agent = r.get("selected_agent") or "—"
        lines.append(
            f"| `{r['id']}` | {case.get('description', '')} | {agent} | {tools} | {icon} {('PASS' if r['passed'] else 'FAIL')} | {r['latency_ms']}ms |"
        )

    lines += ["", "---", "", "## Failures", ""]
    failures_found = False
    for r in results:
        if not r["passed"]:
            failures_found = True
            lines.append(f"### `{r['id']}` — {case_map.get(r['id'], {}).get('description', '')}")
            for f in r["failures"]:
                lines.append(f"- {f}")
            lines.append("")

    if not failures_found:
        lines.append("_All cases passed — no failures._")

    lines += [
        "",
        "---",
        "",
        "## Summary",
        "",
        f"- **Passed:** {passed_count}/{total}",
        f"- **Failed:** {total - passed_count}/{total}",
        f"- **Pass rate:** {round(passed_count/total*100)}%",
        f"- **Total elapsed:** {round(elapsed_s, 2)}s",
        f"- **Avg latency:** {round(sum(r['latency_ms'] for r in results) / total)}ms",
    ]

    path = output_dir / f"{timestamp}_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


async def run_all(base_url: str, verbose: bool, output_dir: Path) -> None:
    cases: list[dict] = json.loads(EVALS_FILE.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")

    print(f"\nRunning {len(cases)} eval cases against {base_url}\n")
    print(f"{'ID':<12} {'Description':<45} {'Result':<10} {'Latency'}")
    print("-" * 90)

    suite_start = time.perf_counter()

    async with httpx.AsyncClient(base_url=base_url, timeout=120.0) as client:
        for case in cases:
            start = time.perf_counter()
            # Use a timestamped conversation_id so each eval run starts with a
            # fresh conversation history (no contamination from previous runs).
            input_payload = {
                **case["input"],
                "conversation_id": f"{case['input']['conversation_id']}-{timestamp}",
            }
            try:
                resp = await client.post("/agent/respond", json=input_payload)
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
                    print(f"           -> {f}")

            results.append({
                "id": case["id"],
                "description": case.get("description", ""),
                "passed": passed,
                "failures": failures,
                "latency_ms": latency,
                "selected_agent": data.get("selected_agent"),
                "tools_used": data.get("tools_used", []),
                "expected_agent": case.get("expected_agent"),
                "safety_behavior": case.get("safety_behavior"),
            })

    elapsed_s = time.perf_counter() - suite_start
    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])

    print("-" * 90)
    print(f"\nResults: {passed_count}/{total} passed ({round(passed_count/total*100)}%)")
    print(f"Elapsed: {round(elapsed_s, 2)}s\n")

    json_path = save_json_report(results, cases, passed_count, base_url, elapsed_s, output_dir, timestamp)
    md_path = save_markdown_report(results, cases, passed_count, base_url, elapsed_s, output_dir, timestamp)

    print(f"Reports saved:")
    print(f"  JSON → {json_path}")
    print(f"  MD   → {md_path}\n")

    if passed_count < total:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run streaming-support-agent evals")
    parser.add_argument(
        "--base-url", default="http://localhost:8000", help="Base URL of the running API"
    )
    parser.add_argument("--verbose", action="store_true", help="Show failure details")
    parser.add_argument(
        "--output",
        default=str(REPORTS_DIR),
        help="Directory to save JSON and Markdown reports (default: evals/reports/)",
    )
    args = parser.parse_args()

    asyncio.run(run_all(args.base_url, args.verbose, Path(args.output)))

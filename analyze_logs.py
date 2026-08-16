#!/usr/bin/env python3
"""Analyze logs to understand classification pipeline decisions."""

import sys
import re
from collections import defaultdict
from pathlib import Path

def read_logs(log_file: str = None) -> list:
    """Read log file or parse from stdin."""
    if log_file:
        return Path(log_file).read_text().split("\n")
    return sys.stdin.read().split("\n")

def parse_log_line(line: str) -> dict:
    """Extract relevant info from a log line."""
    result = {"raw": line}

    # Pattern: 🔴 [TYPE] Message
    if "🔴" in line or "✓" in line or "⚠️" in line or "→" in line:
        result["highlighted"] = True

    # LLM CALL
    if "[LLM CALL]" in line:
        result["type"] = "llm_call"
        match = re.search(r"Sending to (\w+):\s*(.*?)$", line)
        if match:
            result["provider"] = match.group(1)
            result["subject"] = match.group(2).strip()

    # LLM RESULT
    elif "[LLM RESULT]" in line:
        result["type"] = "llm_result"
        match = re.search(r"Category:\s*(\w+)\s*\|\s*Priority:\s*(\d+)\s*\|\s*([\d.]+)s", line)
        if match:
            result["category"] = match.group(1)
            result["priority"] = int(match.group(2))
            result["elapsed"] = float(match.group(3))

    # LLM ERROR
    elif "[LLM ERROR]" in line:
        result["type"] = "llm_error"

    # LOCAL INTEL HIT
    elif "LOCAL INTEL" in line:
        result["type"] = "local_hit"
        match = re.search(r"\|\s*(.*?)\s*\|\s*category:\s*(\w+)", line)
        if match:
            result["subject"] = match.group(1).strip()
            result["category"] = match.group(2)

    # SENDER OVERRIDE
    elif "SENDER OVERRIDE" in line:
        result["type"] = "sender_override"
        match = re.search(r"\|\s*(.*?)\s*\|\s*from:", line)
        if match:
            result["subject"] = match.group(1).strip()

    # DYNAMIC LABEL
    elif "DYNAMIC LABEL" in line:
        result["type"] = "dynamic_label"
        match = re.search(r"\|\s*(.*?)\s*\|\s*category:", line)
        if match:
            result["subject"] = match.group(1).strip()

    return result

def analyze(log_file: str = None) -> None:
    """Analyze log file and print statistics."""
    lines = read_logs(log_file)
    events = [parse_log_line(line) for line in lines if line.strip()]
    events = [e for e in events if e.get("type")]

    # Count by type
    counts = defaultdict(int)
    categories_used = defaultdict(int)
    elapsed_times = []

    for event in events:
        counts[event["type"]] += 1
        if event.get("category"):
            categories_used[event["category"]] += 1
        if event.get("elapsed"):
            elapsed_times.append(event["elapsed"])

    print("\n" + "="*70)
    print("📊 CLASSIFICATION PIPELINE ANALYSIS")
    print("="*70)

    total = sum(counts.values())
    print(f"\n📈 Summary (Total: {total} emails)")
    print(f"  ✓ Sender Override:    {counts['sender_override']:>4}  ({100*counts['sender_override']/total:>5.1f}%)")
    print(f"  ✓ Dynamic Labels:     {counts['dynamic_label']:>4}  ({100*counts['dynamic_label']/total:>5.1f}%)")
    print(f"  ✓ Local Intelligence: {counts['local_hit']:>4}  ({100*counts['local_hit']/total:>5.1f}%)")
    print(f"  🔴 LLM Required:      {counts['llm_call']:>4}  ({100*counts['llm_call']/total:>5.1f}%)")
    print(f"  ⚠️  LLM Errors:        {counts['llm_error']:>4}  ({100*counts.get('llm_error', 0)/total:>5.1f}%)")

    # LLM efficiency
    skipped_llm = counts['sender_override'] + counts['dynamic_label'] + counts['local_hit']
    print(f"\n💡 Efficiency:")
    print(f"  Emails that SKIPPED LLM: {skipped_llm} ({100*skipped_llm/total:.1f}%)")
    print(f"  Emails that NEEDED LLM:  {counts['llm_call']} ({100*counts['llm_call']/total:.1f}%)")

    # Categories
    if categories_used:
        print(f"\n📂 Categories Used:")
        for cat, count in sorted(categories_used.items(), key=lambda x: x[1], reverse=True):
            pct = 100 * count / total
            print(f"  {cat:20} {count:>4}  ({pct:>5.1f}%)")

    # Performance
    if elapsed_times:
        avg_time = sum(elapsed_times) / len(elapsed_times)
        max_time = max(elapsed_times)
        min_time = min(elapsed_times)
        print(f"\n⏱️  LLM Response Times (n={len(elapsed_times)}):")
        print(f"  Average: {avg_time:.2f}s")
        print(f"  Min:     {min_time:.2f}s")
        print(f"  Max:     {max_time:.2f}s")

    # Show LLM-only emails
    print(f"\n🔴 Emails Requiring LLM:")
    llm_emails = [e for e in events if e["type"] == "llm_call"]
    for i, email in enumerate(llm_emails[:10], 1):
        provider = email.get("provider", "?").upper()
        subject = email.get("subject", "?")[:50]
        print(f"  {i:2}. [{provider}] {subject}")

    if len(llm_emails) > 10:
        print(f"  ... and {len(llm_emails) - 10} more")

    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    log_file = sys.argv[1] if len(sys.argv) > 1 else None
    analyze(log_file)

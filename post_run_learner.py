#!/usr/bin/env python3
"""Post-run analysis: suggest new automation rules from LLM classifications."""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

def extract_llm_classifications(log_file: str) -> List[Dict]:
    """Extract emails that were classified by LLM from logs."""
    if not Path(log_file).exists():
        print(f"❌ Log file not found: {log_file}")
        return []

    events = []
    with open(log_file) as f:
        for line in f:
            # Look for LLM CALL and RESULT patterns
            if "[LLM CALL]" in line:
                match = re.search(r"Sending to (\w+):\s*(.*?)$", line)
                if match:
                    events.append({
                        "type": "llm_call",
                        "subject": match.group(2).strip()
                    })
            elif "[LLM RESULT]" in line:
                match = re.search(
                    r"Category:\s*(\w+)\s*\|\s*Priority:\s*(\d+)\s*\|\s*([\d.]+)s\s*\|\s*(.+?)$",
                    line
                )
                if match and events and events[-1]["type"] == "llm_call":
                    events[-1]["type"] = "llm_classified"
                    events[-1]["category"] = match.group(1)
                    events[-1]["priority"] = int(match.group(2))
                    events[-1]["elapsed"] = float(match.group(3))
                    events[-1]["subject"] = match.group(4)

    return [e for e in events if e.get("type") == "llm_classified"]

def analyze_llm_patterns(classifications: List[Dict]) -> Dict:
    """Identify patterns in LLM-classified emails."""
    patterns = defaultdict(lambda: {
        "count": 0,
        "subjects": [],
        "priorities": [],
        "avg_time": 0
    })

    for item in classifications:
        cat = item["category"]
        patterns[cat]["count"] += 1
        patterns[cat]["subjects"].append(item["subject"][:50])
        patterns[cat]["priorities"].append(item["priority"])
        patterns[cat]["elapsed"] = item.get("elapsed", 0)

    # Calculate averages
    for cat in patterns:
        if patterns[cat]["priorities"]:
            patterns[cat]["avg_priority"] = sum(patterns[cat]["priorities"]) / len(patterns[cat]["priorities"])
        else:
            patterns[cat]["avg_priority"] = 3

    return dict(patterns)

def suggest_domain_rules(classifications: List[Dict]) -> List[Dict]:
    """Suggest sender domain rules that could skip LLM."""
    domain_patterns = defaultdict(lambda: {
        "categories": defaultdict(int),
        "subjects": [],
        "count": 0
    })

    for item in classifications:
        # Try to extract domain from subject or context
        # In reality, we'd need the sender email which isn't in the log
        # So we'll use category patterns as proxy
        pass

    return []

def generate_report(log_file: str) -> None:
    """Generate post-run learning report."""
    classifications = extract_llm_classifications(log_file)

    if not classifications:
        print("\n✅ No LLM classifications found in log.")
        print("   All emails were handled by sender overrides, dynamic labels, or local intelligence!")
        return

    patterns = analyze_llm_patterns(classifications)
    total_llm = len(classifications)
    total_time = sum(c.get("elapsed", 0) for c in classifications)

    print("\n" + "="*70)
    print("🔍 POST-RUN LEARNING ANALYSIS")
    print("="*70)

    print(f"\n📊 LLM Usage Summary:")
    print(f"   Total LLM calls: {total_llm}")
    print(f"   Total time:      {total_time:.2f}s")
    print(f"   Avg per email:   {total_time/total_llm:.2f}s")
    print(f"   Est. cost:       ${total_llm * 0.0002:.3f}")

    print(f"\n📂 Classifications by Category:")
    for cat, data in sorted(patterns.items(), key=lambda x: x[1]["count"], reverse=True):
        count = data["count"]
        pct = 100 * count / total_llm
        avg_pri = data["avg_priority"]
        print(f"\n   {cat.upper():20} {count:3} emails ({pct:5.1f}%)")
        print(f"   Average priority: {avg_pri:.1f}")
        print(f"   Sample subjects:")
        for subject in data["subjects"][:3]:
            print(f"      • {subject}")

    print(f"\n{'='*70}")
    print("💡 SUGGESTIONS FOR AUTOMATION")
    print("="*70)

    print(f"""
The emails above were classified by LLM. To automate future similar emails:

1️⃣  ANALYZE PATTERNS
    Run pattern analysis to find sender domains:

    $ python agent.py --analyze-patterns --limit 500

    This will discover patterns like:
    • emails from "noreply@specific-company.com" → always "action_needed"
    • emails from "alerts@bank.com" → always "banking_investment"
    • subject keywords → categories

2️⃣  REVIEW SUGGESTIONS
    Check the generated file:
    $ cat data/pattern_review.md

    Shows confidence scores for each pattern.

3️⃣  CONFIRM NEW LABELS
    For patterns you trust (>80% confidence):

    $ python agent.py --confirm-label payroll.company.com work
    $ python agent.py --confirm-label alerts.bank.com banking_investment

    This adds them to data/dynamic_labels.json

4️⃣  IMPROVE LOCAL RULES
    The local intelligence system learns from each LLM classification.
    Each run should increase local hits and decrease LLM calls.

    Monitor with:
    $ python monitor_efficiency.py

⏭️  NEXT STEPS
""")

    # Show which categories had most LLM calls
    top_cats = sorted(patterns.items(), key=lambda x: x[1]["count"], reverse=True)[:3]
    if top_cats:
        print("   High-volume categories to focus on:")
        for cat, data in top_cats:
            print(f"   • {cat} ({data['count']} emails) → Good candidates for automation")

    print(f"\n{'='*70}\n")

def interactive_prompt() -> None:
    """Prompt user to run analysis."""
    print("\n🤖 Would you like to analyze patterns now? (y/n): ", end="")
    choice = input().strip().lower()

    if choice == 'y':
        print("\n⏳ Starting pattern analysis...")
        import subprocess
        result = subprocess.run(
            ["python", "agent.py", "--analyze-patterns", "--limit", "500"],
            capture_output=False
        )

        if result.returncode == 0:
            print("\n✅ Analysis complete! Check data/pattern_review.md")
            print("   Use: python agent.py --confirm-label <domain> <category>")

if __name__ == "__main__":
    import sys

    log_file = sys.argv[1] if len(sys.argv) > 1 else "logs/digest.log"
    generate_report(log_file)

    # Only prompt if there were classifications
    classifications = extract_llm_classifications(log_file)
    if classifications:
        interactive_prompt()

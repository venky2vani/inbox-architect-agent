#!/usr/bin/env python3
"""Monitor local intelligence learning efficiency."""

import json
from pathlib import Path
from typing import Dict, List, Tuple

def load_rules() -> List[Dict]:
    """Load local rules from JSON."""
    path = Path("data/local_rules.json")
    if not path.exists():
        print("❌ No rules file found at data/local_rules.json")
        return []

    with open(path) as f:
        return json.load(f).get("rules", [])

def calculate_confidence(rule: Dict) -> float:
    """Calculate rule confidence (hits / total)."""
    hits = rule.get("hits", 0)
    misses = rule.get("misses", 0)
    total = hits + misses
    return hits / total if total > 0 else 0.0

def analyze_rules() -> None:
    """Analyze and display rule efficiency."""
    rules = load_rules()

    if not rules:
        print("📊 No rules learned yet. Process more emails to build rules.")
        return

    print(f"\n📊 Local Intelligence Report\n" + "="*60)
    print(f"Total rules learned: {len(rules)}")

    # Group by type
    by_type: Dict[str, List] = {}
    for rule in rules:
        rule_type = rule.get("type", "unknown")
        if rule_type not in by_type:
            by_type[rule_type] = []
        by_type[rule_type].append(rule)

    # Statistics per type
    print(f"\n📋 Rules by Type:")
    for rule_type, rules_of_type in sorted(by_type.items()):
        count = len(rules_of_type)
        total_hits = sum(r.get("hits", 0) for r in rules_of_type)
        total_misses = sum(r.get("misses", 0) for r in rules_of_type)
        confidence = total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0
        print(f"  {rule_type:20} {count:3} rules  {confidence:6.1%} confidence  ({total_hits} hits, {total_misses} misses)")

    # Top performing rules (high confidence, many hits)
    print(f"\n🌟 Top Performing Rules (highest confidence):")
    sorted_rules = sorted(rules, key=lambda r: calculate_confidence(r), reverse=True)
    for i, rule in enumerate(sorted_rules[:10], 1):
        conf = calculate_confidence(rule)
        hits = rule.get("hits", 0)
        misses = rule.get("misses", 0)
        value = rule.get("value", "?")
        category = rule.get("category", "?")
        print(f"  {i:2}. [{conf:6.1%}] {rule['type']:18} → {category:15} ({hits}H/{misses}M) {value[:40]}")

    # Rules that need work (high misses)
    print(f"\n⚠️  Rules Needing Work (many misses):")
    sorted_by_misses = sorted(rules, key=lambda r: r.get("misses", 0), reverse=True)
    for i, rule in enumerate(sorted_by_misses[:10], 1):
        hits = rule.get("hits", 0)
        misses = rule.get("misses", 0)
        conf = calculate_confidence(rule)
        value = rule.get("value", "?")
        category = rule.get("category", "?")
        if misses > 0:
            print(f"  {i:2}. [{conf:6.1%}] {rule['type']:18} → {category:15} ({hits}H/{misses}M) {value[:40]}")

    # Overall effectiveness
    total_hits = sum(r.get("hits", 0) for r in rules)
    total_misses = sum(r.get("misses", 0) for r in rules)
    overall_conf = total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0

    print(f"\n📈 Overall Metrics:")
    print(f"  Total hits:        {total_hits:>6}")
    print(f"  Total misses:      {total_misses:>6}")
    print(f"  Overall confidence: {overall_conf:>6.1%}")
    print(f"  Reliability: {get_reliability(overall_conf)}")
    print("="*60 + "\n")

def get_reliability(confidence: float) -> str:
    """Return human-readable reliability assessment."""
    if confidence >= 0.85:
        return "🟢 Excellent  (can skip LLM most of the time)"
    elif confidence >= 0.70:
        return "🟡 Good       (can skip LLM ~70% of the time)"
    elif confidence >= 0.50:
        return "🟠 Fair       (need more data)"
    else:
        return "🔴 Poor       (still learning)"

if __name__ == "__main__":
    analyze_rules()

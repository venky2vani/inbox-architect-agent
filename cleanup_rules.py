#!/usr/bin/env python3
"""Clean up low-confidence and malformed rules to improve classification accuracy."""

import json
from pathlib import Path
from collections import defaultdict

def cleanup_rules(rules_file: str = "data/local_rules.json", confidence_threshold: float = 0.65, aggressive: bool = True):
    """Remove problematic rules to improve overall accuracy.

    Args:
        aggressive: If True, aggressively remove weak keywords to improve local intelligence hit rate.
    """

    rules_path = Path(rules_file)
    if not rules_path.exists():
        print(f"❌ Rules file not found: {rules_file}")
        return

    with open(rules_path) as f:
        data = json.load(f)

    original_count = len(data.get('rules', []))
    rules = data['rules']

    # Rules to delete
    to_delete = []
    stats = defaultdict(int)

    # Aggressive: Delete these specific weak keywords entirely (not just low-confidence samples)
    weak_keywords = {
        'payment',    # 39.1% - catastrophically weak
        'please',     # 37.2% - catastrophically weak
        'com',        # 60.8% - too generic
        'card',       # 58.8% - ambiguous
        'alert',      # 58.9% - ambiguous
        'credit',     # 59.9% - ambiguous
        'bank',       # Often misclassified
        'account',    # Too generic
        'confirm',    # Ambiguous
        'update',     # Ambiguous
    }

    for idx, rule in enumerate(rules):
        hits = rule.get('hits', 0)
        misses = rule.get('misses', 0)
        total = hits + misses
        feature_value = rule.get('value', '').strip().lower()
        feature_type = rule.get('type', '')

        # Reason 1: Malformed rules (empty feature value)
        if not feature_value or feature_value == 'unknown':
            to_delete.append(idx)
            stats['malformed'] += 1
            continue

        # Reason 2: Aggressive - delete weak keywords entirely
        if aggressive and (feature_type in ('subject_keyword', 'body_keyword')) and feature_value in weak_keywords:
            to_delete.append(idx)
            stats['weak_keyword_aggressive'] += 1
            continue

        # Reason 3: Too generic keywords (appear in almost everything)
        generic_keywords = {
            'https', 'http', '.co', '.in', 'email', 'address',
            'click', 'here', 'link', 'website', 'contact', 'thank'
        }
        if feature_type == 'body_keyword' and feature_value in generic_keywords:
            to_delete.append(idx)
            stats['generic_keyword'] += 1
            continue

        # Reason 4: Ambiguous keywords - delete ALL samples (not just <20)
        ambiguous_keywords = {'card', 'alert', 'payment', 'update', 'confirm'}
        if feature_type == 'subject_keyword' and feature_value in ambiguous_keywords:
            to_delete.append(idx)
            stats['ambiguous_keyword'] += 1
            continue

        # Reason 5: Very low confidence with few hits
        if total >= 5 and hits < 2:  # < 40% confidence and few successes
            to_delete.append(idx)
            stats['very_low_confidence'] += 1
            continue

        # Reason 6: Weak sender domain rules
        if feature_type == 'sender_domain' and total >= 10:
            confidence = hits / total
            if confidence < 0.50:  # Lowered from 0.45 to 0.50
                to_delete.append(idx)
                stats['weak_domain'] += 1
                continue

        # Reason 7: Low confidence general rules (aggressive threshold)
        if aggressive and total >= 10:
            confidence = hits / total
            if confidence < confidence_threshold:  # 0.65 by default
                to_delete.append(idx)
                stats['low_confidence_aggressive'] += 1
                continue

    # Delete in reverse order to maintain indices
    deleted_count = 0
    for idx in sorted(to_delete, reverse=True):
        del rules[idx]
        deleted_count += 1

    # Save cleaned rules
    data['rules'] = rules
    with open(rules_path, 'w') as f:
        json.dump(data, f, indent=2)

    # Report
    print("\n" + "=" * 70)
    print("🧹 RULE CLEANUP REPORT")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"  Original rules:     {original_count}")
    print(f"  Deleted rules:      {deleted_count}")
    print(f"  Remaining rules:    {len(rules)}")
    print(f"  Improvement:        {100 * deleted_count / original_count:.1f}% cleaned")

    print(f"\n🎯 Breakdown:")
    for reason, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            reason_text = {
                'malformed': '❌ Malformed (empty/unknown feature)',
                'weak_keyword_aggressive': '🔴 Weak keywords (payment, please, com, etc)',
                'generic_keyword': '🔴 Generic keywords (https, .com, etc)',
                'ambiguous_keyword': '🟠 Ambiguous keywords (card, alert, etc)',
                'very_low_confidence': '🟡 Very low confidence (<40%)',
                'low_confidence_aggressive': '🟡 Low confidence aggressive (<65%)',
                'weak_domain': '🟡 Weak sender domain rules (<50%)'
            }
            print(f"  {reason_text.get(reason, reason):45} {count:4} rules")

    print(f"\n✅ Cleaned rules saved to: {rules_file}")
    print(f"\n💡 Impact: Removed weak keywords to improve local intelligence hit rate")
    print(f"   Next step: Run a new digest cycle to learn better rules")
    print("   $ python agent.py --limit 500")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    import sys
    aggressive = '--aggressive' in sys.argv or True  # Default to aggressive
    cleanup_rules(aggressive=aggressive)

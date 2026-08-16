#!/usr/bin/env python3
"""Clean up low-confidence and malformed rules to improve classification accuracy."""

import json
from pathlib import Path
from collections import defaultdict

def cleanup_rules(rules_file: str = "data/local_rules.json", confidence_threshold: float = 0.55):
    """Remove problematic rules to improve overall accuracy."""

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

        # Reason 2: Too generic keywords (appear in almost everything)
        generic_keywords = {
            'https', 'http', '.com', '.co', '.in', 'email', 'address',
            'click', 'here', 'link', 'website', 'contact', 'thank'
        }
        if feature_type == 'body_keyword' and feature_value in generic_keywords:
            to_delete.append(idx)
            stats['generic_keyword'] += 1
            continue

        # Reason 3: Too ambiguous single-word keywords
        ambiguous_keywords = {'card', 'alert', 'payment', 'update', 'confirm'}
        if feature_type == 'subject_keyword' and feature_value in ambiguous_keywords:
            if total < 20:  # Only delete if few samples
                to_delete.append(idx)
                stats['ambiguous_keyword'] += 1
                continue

        # Reason 4: Very low confidence with few hits
        if total >= 5 and hits < 2:  # < 40% confidence and few successes
            to_delete.append(idx)
            stats['very_low_confidence'] += 1
            continue

        # Reason 5: Weak sender domain rules
        if feature_type == 'sender_domain' and total >= 10:
            confidence = hits / total
            if confidence < 0.45:  # < 45% for sender domains
                to_delete.append(idx)
                stats['weak_domain'] += 1
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
                'generic_keyword': '🔴 Generic keywords (https, .com, etc)',
                'ambiguous_keyword': '🟠 Ambiguous keywords (card, alert, payment)',
                'very_low_confidence': '🟡 Very low confidence (<40%)',
                'weak_domain': '🟡 Weak sender domain rules (<45%)'
            }
            print(f"  {reason_text.get(reason, reason):45} {count:4} rules")

    print(f"\n✅ Cleaned rules saved to: {rules_file}")
    print(f"\n💡 Next step: Run a new digest cycle to learn better rules")
    print("   $ python agent.py --limit 500")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    cleanup_rules()

#!/bin/bash
# Complete workflow: run agent → analyze learning → suggest improvements

set -e

echo "📧 Inbox Architect Learning Loop"
echo "=================================="

# Step 1: Run the daily digest
LOG_FILE="logs/digest.log"
mkdir -p logs

echo ""
echo "1️⃣  Running daily digest..."
python agent.py --log-level INFO --log-file "$LOG_FILE" "$@"

# Step 2: Show log analysis
echo ""
echo "2️⃣  Analyzing classification pipeline..."
python analyze_logs.py "$LOG_FILE"

# Step 3: Show efficiency metrics
echo ""
echo "3️⃣  Checking learning efficiency..."
python monitor_efficiency.py

# Step 4: Post-run learning analysis
echo ""
echo "4️⃣  Learning opportunities..."
python post_run_learner.py "$LOG_FILE"

echo ""
echo "✅ Complete! Check the suggestions above to improve automation."
echo ""
echo "Next time, fewer emails will need LLM processing. 🚀"

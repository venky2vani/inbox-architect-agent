# Running Inbox Architect Agent Locally

The agent requires browser-based OAuth authentication, so you need to run it in your local terminal, not in Claude Code.

## Quick Start (Copy & Paste)

Open your terminal and run:

```bash
cd /home/venkatesh/inbox-architect-agent
source .venv/bin/activate
python agent.py --dry-run --limit 5
```

## What Happens

1. **First time only:** A browser window opens asking "Allow Inbox Architect Agent to access your Gmail?"
2. Click **Allow**
3. You'll see a success page
4. The agent processes your emails and shows a summary
5. A token is saved to `credentials/token.json` for future runs (no more auth needed)

## Useful Commands

```bash
# Test with 5 emails (safe, no side effects)
python agent.py --dry-run --limit 5

# Test with 10 emails
python agent.py --dry-run --limit 10

# Process all unread emails (actually archives noise emails)
python agent.py

# Don't auto-archive noise
python agent.py --no-archive

# See all options
python agent.py --help
```

## Troubleshooting

**Problem:** "No module named 'plugins'"
**Solution:** Make sure you're in the project directory and activated the venv

**Problem:** "credentials.json not found"
**Solution:** Check that `credentials/credentials.json` exists

**Problem:** "ModuleNotFoundError"
**Solution:** Run `pip install -r requirements.txt` after activating venv

---

Once you've authorized via browser, the agent is ready to use! 🚀

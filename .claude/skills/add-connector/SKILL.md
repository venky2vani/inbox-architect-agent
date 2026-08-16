---
name: add-connector
description: Create a new email connector plugin (Outlook, ProtonMail, etc.)
arguments: [connector-name]
---

## Current Connector Plugins

!`cd ${CLAUDE_PROJECT_DIR} && ls -1 plugins/*_connector.py 2>/dev/null | xargs basename -a | sed 's/\.py$//'`

## Base Class Reference

!`cd ${CLAUDE_PROJECT_DIR} && grep -A 20 "class EmailConnector" plugins/base.py | head -25`

## Task

Create a new email connector named `$connector_name` with:

1. **File**: `plugins/${connector_name}_connector.py`
2. **Class name**: `${connector_name}Connector` (e.g., `OutlookConnector`)
3. **Inheritance**: Must extend `EmailConnector` from `plugins/base.py`
4. **Auto-discovery**: Orchestrator finds it automatically via naming convention

### Template Structure

```python
from plugins.base import EmailConnector
from typing import List, Dict, Any

class ${connector_name}Connector(EmailConnector):
    """
    Email connector for ${connector_name}.
    
    Fetches emails, handles authentication, and manages message lifecycle.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Initialize connector-specific settings
        pass
    
    def authenticate(self) -> bool:
        """Authenticate with ${connector_name} API."""
        pass
    
    def fetch_unread(self) -> List[Dict[str, Any]]:
        """Fetch unread emails."""
        pass
    
    def get_attachments(self, message_id: str) -> List[Dict[str, Any]]:
        """Download attachments for a message."""
        pass
    
    def archive(self, message_id: str) -> bool:
        """Archive (move to label/folder) a message."""
        pass
    
    def mark_read(self, message_id: str) -> bool:
        """Mark a message as read."""
        pass
```

### Next Steps

1. Implement each method according to the ${connector_name} API docs
2. Add any required dependencies to `requirements.txt`
3. Update `.env.example` with new config variables (e.g., `${connector_name}_API_KEY`)
4. Add unit tests in `tests/test_${connector_name}_connector.py`
5. Test with `/run-agent` to verify auto-discovery

The orchestrator will auto-load your connector on the next run—no code changes needed.
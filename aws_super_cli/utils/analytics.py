"""Optional anonymous usage analytics for AWS Super CLI"""

import hashlib
import json
import platform
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class UsageAnalytics:
    """Lightweight, anonymous usage tracking"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled and REQUESTS_AVAILABLE
        self.session_id = self._get_session_id()
        
    def _get_session_id(self) -> str:
        """Generate anonymous session ID"""
        # Use MAC address hash for consistent but anonymous ID
        mac = hex(uuid.getnode())
        return hashlib.sha256(mac.encode()).hexdigest()[:16]
    
    def track_command(self, command: str, version: str, success: bool = True):
        """Track command usage anonymously"""
        if not self.enabled:
            return
            
        try:
            data = {
                'command': command,
                'version': version,
                'success': success,
                'timestamp': datetime.utcnow().isoformat(),
                'platform': platform.system(),
                'python_version': platform.python_version(),
                'session_id': self.session_id
            }
            
            # Example endpoint - you'd need to set up your own
            # requests.post('https://your-analytics-endpoint.com/track', 
            #               json=data, timeout=2)
            
            # For now, just log locally (optional)
            self._log_locally(data)
            
        except Exception:
            # Never let analytics break the CLI
            pass
    
    def _log_locally(self, data: dict):
        """Optional local logging for debugging"""
        log_file = Path.home() / '.aws-super-cli' / 'usage.log'
        log_file.parent.mkdir(exist_ok=True)
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(data) + '\n')


# Global instance (disabled by default)
analytics = UsageAnalytics(enabled=False) 
"""
Simple token usage tracker for MCP server.
Estimates token usage based on character count (rough approximation).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class TokenTracker:
    """Track estimated token usage for MCP interactions"""
    
    # Rough estimation: 1 token ≈ 4 characters (conservative estimate)
    CHARS_PER_TOKEN = 4
    
    def __init__(self, log_file: str = "mcp_token_usage.json"):
        self.log_file = Path(log_file)
        self.session_tokens = 0
        self.session_start = datetime.utcnow()
        
        # Load existing data if available
        self.usage_data = self._load_usage_data()
    
    def _load_usage_data(self) -> Dict[str, Any]:
        """Load existing usage data from file"""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load token usage data: {e}")
        
        return {
            "total_tokens": 0,
            "sessions": [],
            "daily_usage": {}
        }
    
    def _save_usage_data(self):
        """Save usage data to file"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.usage_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save token usage data: {e}")
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from text"""
        # Simple character-based estimation
        return len(text) // self.CHARS_PER_TOKEN
    
    def track_request(self, request_data: Dict[str, Any]) -> int:
        """Track tokens for a request"""
        text = json.dumps(request_data)
        tokens = self.estimate_tokens(text)
        self.session_tokens += tokens
        return tokens
    
    def track_response(self, response_data: Dict[str, Any]) -> int:
        """Track tokens for a response"""
        text = json.dumps(response_data)
        tokens = self.estimate_tokens(text)
        self.session_tokens += tokens
        return tokens
    
    def end_session(self, agent_id: str):
        """End tracking session and save data"""
        session_data = {
            "agent_id": agent_id,
            "start_time": self.session_start,
            "end_time": datetime.utcnow(),
            "tokens_used": self.session_tokens
        }
        
        # Update total tokens
        self.usage_data["total_tokens"] += self.session_tokens
        
        # Add session data
        self.usage_data["sessions"].append(session_data)
        
        # Update daily usage
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if today not in self.usage_data["daily_usage"]:
            self.usage_data["daily_usage"][today] = 0
        self.usage_data["daily_usage"][today] += self.session_tokens
        
        # Save to file
        self._save_usage_data()
        
        logger.info(f"Session ended for {agent_id}: {self.session_tokens} tokens used")
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get usage summary"""
        return {
            "total_tokens": self.usage_data["total_tokens"],
            "session_tokens": self.session_tokens,
            "daily_usage": self.usage_data.get("daily_usage", {}),
            "recent_sessions": self.usage_data["sessions"][-10:]  # Last 10 sessions
        }
"""Claude API Service for managing API key and connections."""

from anthropic import Anthropic
from datetime import datetime
from pathlib import Path
from typing import Optional
import os


class ClaudeService:
    """Manage Claude API connection with persistent key storage."""

    def __init__(self):
        self.api_key: Optional[str] = None
        self.client: Optional[Anthropic] = None
        self._load_api_key()

    def _load_api_key(self):
        """Load API key from environment or .env file."""
        # First check environment
        key = os.getenv("ANTHROPIC_API_KEY")
        if key and key != "your_key_here":
            self.set_api_key(key, save_to_env=False)
            return

        # Then check .env file
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, "r") as f:
                for line in f:
                    if line.startswith("ANTHROPIC_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        if key and key != "your_key_here":
                            self.set_api_key(key, save_to_env=False)
                        break

    def set_api_key(self, api_key: str, save_to_env: bool = True):
        """Store API key and initialize client."""
        self.api_key = api_key
        self.client = Anthropic(api_key=api_key)
        if save_to_env:
            self._save_to_env(api_key)

    async def test_connection(self) -> dict:
        """
        Test API key validity with minimal token usage.

        Returns:
            {
                'success': bool,
                'model': str,
                'message': str,
                'tested_at': str
            }
        """
        if not self.client:
            return {
                "success": False,
                "model": None,
                "message": "API key not configured",
                "tested_at": datetime.utcnow().isoformat()
            }

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )

            return {
                "success": True,
                "model": response.model,
                "message": "Connection successful",
                "tested_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "model": None,
                "message": f"Connection failed: {str(e)}",
                "tested_at": datetime.utcnow().isoformat()
            }

    def _save_to_env(self, api_key: str):
        """Persist API key to .env file."""
        env_file = Path(".env")
        lines = []

        if env_file.exists():
            with open(env_file, "r") as f:
                lines = f.readlines()

        # Update or add key
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("ANTHROPIC_API_KEY="):
                lines[i] = f"ANTHROPIC_API_KEY={api_key}\n"
                updated = True
                break

        if not updated:
            lines.append(f"ANTHROPIC_API_KEY={api_key}\n")

        with open(env_file, "w") as f:
            f.writelines(lines)

    def get_masked_key(self) -> Optional[str]:
        """Return masked version of API key for display."""
        if not self.api_key:
            return None
        if len(self.api_key) > 12:
            return f"{self.api_key[:8]}...{self.api_key[-4:]}"
        return "****"

    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return self.api_key is not None and len(self.api_key) > 0


# Global service instance
claude_service = ClaudeService()

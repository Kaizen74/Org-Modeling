"""Tests for Claude API service."""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.claude_service import ClaudeService


def test_api_key_storage():
    """Test API key can be stored."""
    service = ClaudeService()
    test_key = "sk-ant-test123456789"
    service.set_api_key(test_key, save_to_env=False)
    assert service.api_key == test_key
    assert service.is_configured() is True


def test_masked_key():
    """Test API key masking."""
    service = ClaudeService()
    service.api_key = "sk-ant-api123456789test"
    masked = service.get_masked_key()
    assert masked is not None
    assert "..." in masked
    assert "sk-ant-a" in masked


def test_not_configured():
    """Test when no key is configured."""
    service = ClaudeService()
    service.api_key = None
    service.client = None
    assert service.is_configured() is False
    assert service.get_masked_key() is None


@pytest.mark.asyncio
async def test_connection_without_key():
    """Test connection test without API key."""
    service = ClaudeService()
    service.api_key = None
    service.client = None
    result = await service.test_connection()
    assert result["success"] is False
    assert "not configured" in result["message"]

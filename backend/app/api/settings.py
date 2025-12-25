"""Settings API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..services.claude_service import claude_service

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class APIKeyRequest(BaseModel):
    api_key: str


class APIKeyStatus(BaseModel):
    configured: bool
    masked_key: Optional[str] = None


class ConnectionTestResult(BaseModel):
    success: bool
    model: Optional[str] = None
    message: str
    tested_at: str


@router.post("/claude-api-key")
async def set_claude_api_key(request: APIKeyRequest):
    """Set the Claude API key."""
    if not request.api_key or len(request.api_key) < 10:
        raise HTTPException(status_code=400, detail="Invalid API key format")

    claude_service.set_api_key(request.api_key)
    return {"message": "API key saved", "masked_key": claude_service.get_masked_key()}


@router.post("/claude-api-key/test", response_model=ConnectionTestResult)
async def test_claude_connection():
    """Test the Claude API connection."""
    result = await claude_service.test_connection()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/claude-api-key/status", response_model=APIKeyStatus)
async def get_claude_status():
    """Check if Claude API key is configured."""
    return APIKeyStatus(
        configured=claude_service.is_configured(),
        masked_key=claude_service.get_masked_key()
    )

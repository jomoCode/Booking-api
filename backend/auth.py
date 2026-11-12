import os

from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

# Set ADMIN_API_KEY in Render's environment settings. The default is only for local dev.
API_KEY = os.getenv("ADMIN_API_KEY", "my-secret-clinic-key-123")
API_KEY_NAME = "x-api-key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def verify_api_key(api_key: str = Security(api_key_header)):
    """Dependency that checks if the incoming request has a valid API key."""
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key"
        )
    return api_key
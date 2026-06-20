from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from shared.auth import verify_credentials

security = HTTPBasic()


def require_admin(
    credentials: HTTPBasicCredentials = Depends(security),
) -> str:
    """FastAPI dependency — only authenticated admins can upload or delete."""
    if not verify_credentials(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

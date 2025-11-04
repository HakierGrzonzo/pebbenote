from typing import Annotated
from fastapi.security import APIKeyHeader
from fastapi import Depends, HTTPException, status
from .config import settings

api_key = APIKeyHeader(name="x-temp-key", auto_error=False)


async def validate_api_key(api_key: Annotated[str | None, Depends(api_key)]):
    if settings.TEMP_API_KEY is None:
        return

    if api_key != settings.TEMP_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

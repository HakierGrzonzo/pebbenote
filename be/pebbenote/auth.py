from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from .config import settings

bearer = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing access token",
        headers={"WWW-Authenticate": "Bearer"},
    )


@lru_cache
def get_jwk_client() -> PyJWKClient:
    # PyJWKClient caches the fetched keys
    return PyJWKClient(f"{settings.OIDC_ISSUER}/protocol/openid-connect/certs")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    jwk_client: Annotated[PyJWKClient, Depends(get_jwk_client)],
) -> str:
    """Validate the Keycloak access token and return its subject."""
    if credentials is None:
        raise _unauthorized()

    try:
        signing_key = jwk_client.get_signing_key_from_jwt(credentials.credentials)
        claims = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.OIDC_ISSUER,
            audience=settings.OIDC_AUDIENCE,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError:
        raise _unauthorized()

    return claims["sub"]


CurrentUser = Annotated[str, Depends(get_current_user)]

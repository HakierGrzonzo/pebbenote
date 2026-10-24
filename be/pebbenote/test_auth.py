import time
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from .auth import get_current_user
from .config import settings


def make_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeJwkClient:
    def __init__(self, key) -> None:
        self.key = key

    def get_signing_key_from_jwt(self, token: str):
        return SimpleNamespace(key=self.key.public_key())


class GetCurrentUserTestCase(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.key = make_key()
        self.jwk_client = FakeJwkClient(self.key)

    def token(self, key=None, **overrides) -> str:
        claims = {
            "sub": "user-a",
            "iss": settings.OIDC_ISSUER,
            "aud": settings.OIDC_AUDIENCE,
            "exp": int(time.time()) + 60,
        } | overrides
        claims = {k: v for k, v in claims.items() if v is not None}
        return jwt.encode(claims, key or self.key, algorithm="RS256")

    async def authenticate(self, token: str | None) -> str:
        credentials = (
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            if token
            else None
        )
        return await get_current_user(credentials, self.jwk_client)  # type: ignore

    async def assert_rejected(self, token: str | None):
        with self.assertRaises(HTTPException) as ctx:
            await self.authenticate(token)
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_valid_token_returns_subject(self):
        self.assertEqual(await self.authenticate(self.token()), "user-a")

    async def test_missing_token(self):
        await self.assert_rejected(None)

    async def test_garbage_token(self):
        await self.assert_rejected("not-a-jwt")

    async def test_expired_token(self):
        await self.assert_rejected(self.token(exp=int(time.time()) - 60))

    async def test_wrong_issuer(self):
        await self.assert_rejected(self.token(iss="https://evil.example"))

    async def test_wrong_audience(self):
        await self.assert_rejected(self.token(aud="someone-else"))

    async def test_missing_subject(self):
        await self.assert_rejected(self.token(sub=None))

    async def test_bad_signature(self):
        await self.assert_rejected(self.token(key=make_key()))

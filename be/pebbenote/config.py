from typing import Literal

from pydantic_settings import BaseSettings

type AiProviderKinds = Literal["Ollama", "OpenAI", "Null"]

type EnvironmentKinds = Literal["local", "stage"]


class AppSettings(BaseSettings):
    POSTGRES_DB: str = "postgres"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_LOG_QUERIES: bool = False

    AI_PROVIDER: AiProviderKinds = "Ollama"
    CHAT_MODEL: str = "gemma4:e2b"
    DECISION_MODEL: str = "nimble"

    OIDC_ISSUER: str = "http://localhost:8080/realms/pebbenote"
    OIDC_AUDIENCE: str = "pebbenote-be"

    ENVIRONMENT: EnvironmentKinds = "local"

    REDIS_URL: str = "redis://localhost:6379"
    # How long POST /action/ waits for the LLM before answering 202 Accepted
    ACTION_WAIT_SECONDS: float = 10
    ACTION_MAX_RETRIES: int = 3


settings = AppSettings()

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

    ENVIRONMENT: EnvironmentKinds = "local"


settings = AppSettings()

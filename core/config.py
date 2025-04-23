from typing import Annotated, Any, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import (
    AnyUrl,
    BeforeValidator,
    BaseModel,
    computed_field,
)
from pydantic_core import MultiHostUrl


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class DatabaseCredentials(BaseModel):
    # These are lower case because Optional[x] seems to force it into lowercase
    # Note: env variables can still be uppercase
    username: str
    password: str


class Database(BaseModel):
    ALLOW_FULL_TABLE_OPERATIONS: bool
    CREDENTIAL_SECRET: Optional[str] = None
    CREDENTIALS: Optional[DatabaseCredentials] = None
    HOST: str
    MAX_CONNECTIONS: int
    NAME: str
    PORT: int


class Agent(BaseModel):
    FOUNDATION_MODEL: str
    IS_LOCAL: bool
    HOST: str


class Logger(BaseModel):
    DEBUG: bool
    LOGGER_NAME: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEWS__", env_file=None, env_nested_delimiter="__")

    SERVICE_NAME: str
    DATABASE: Database
    AGENT: Optional[Agent] = None
    LOGGER: Logger
    DOMAIN: str
    PROTOCOL: str
    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DOCUMENTATION_URL(self) -> str:
        return f"/{self.SERVICE_NAME}/docs"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def OPENAPI_URL(self) -> str:
        return f"/{self.SERVICE_NAME}/openapi.json"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URI(self) -> MultiHostUrl:
        # TODO: this needs some logic for whether it's local or running in production
        assert self.DATABASE.CREDENTIALS is not None, "Database credentials are not set"

        return MultiHostUrl.build(
            scheme="postgresql+psycopg2",
            username=self.DATABASE.CREDENTIALS.username,
            password=self.DATABASE.CREDENTIALS.password,
            host=self.DATABASE.HOST,
            port=self.DATABASE.PORT,
            path=self.DATABASE.NAME,
        )


settings = Settings()  # type: ignore[call-arg]

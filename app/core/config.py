import enum
import pathlib

import pydantic
import pydantic_settings

class DatabaseDriver(enum.StrEnum):
    POSTGRESQL = 'postgresql'
    POSTGRESQL_ASYNC = 'postgresql+asyncpg'

class QueueDriver(enum.StrEnum):
    RABBITMQ = 'amqp'

class DatabaseSettings(pydantic_settings.BaseSettings):
    name: str
    host: str
    port: int
    user: str
    password: str
    timeout: int = pydantic.Field(ge=1, le=10, default=2)
    driver: DatabaseDriver = pydantic.Field(default=DatabaseDriver.POSTGRESQL_ASYNC)

    @property
    def async_connection_string(self):
        return (
            f'{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}'
        )

class RabbitmqSettings(pydantic_settings.BaseSettings):

    user: str
    password: str
    host: str
    port: int
    name: str
    driver: QueueDriver = pydantic.Field(default=QueueDriver.RABBITMQ)

    @property
    def connection_string(self):
        return f'{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/'

class ServerSettings(pydantic_settings.BaseSettings):
    listen_address: str
    port: int
    allowed_origins: list[str]

class Config(pydantic_settings.BaseSettings):
    database: DatabaseSettings
    server: ServerSettings
    rabbitmq: RabbitmqSettings

    model_config = pydantic_settings.SettingsConfigDict(
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
    )

env_file = pathlib.Path(__file__).parent.parent.parent.joinpath(f'.env')
settings = Config(_env_file=env_file)
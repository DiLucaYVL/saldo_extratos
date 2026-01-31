"""Configuracoes centralizadas carregadas via .env."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = PROJECT_ROOT / "server"
ENV_FILE = SERVER_DIR / ".env"


class Settings(BaseSettings):
    """Representa as variaveis usadas em todas as fases do plano."""

    db_host: str = Field(alias="DB_HOST")
    db_port: int = Field(alias="DB_PORT")
    db_name: str = Field(alias="DB_NAME")
    db_user: str = Field(alias="DB_USER")
    db_password: str = Field(alias="DB_PASSWORD")
    statements_root: Path | None = Field(default=None, alias="STATEMENTS_ROOT")
    reports_dir: Path | None = Field(default=None, alias="REPORTS_DIR")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=55000, alias="API_PORT")
    drive_root_id: str | None = Field(default=None, alias="DRIVE_ROOT_ID")
    drive_credentials_path: Path | None = Field(default=None, alias="DRIVE_SA_CREDENTIALS_PATH")
    ollama_base_url: str | None = Field(default=None, alias="OLLAMA_BASE_URL")
    ollama_model: str | None = Field(default=None, alias="OLLAMA_MODEL")
    api_base_url: str = Field(default="http://localhost:55000", alias="API_BASE_URL")

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    @field_validator("reports_dir", mode="after")
    @classmethod
    def resolve_reports_dir(cls, v: Path | None) -> Path | None:
        if v is None:
            return None
        if v.is_absolute():
            return v
        # Resolve relative to PROJECT_ROOT
        return (PROJECT_ROOT / v).resolve()

    @property
    def database_url(self) -> str:
        """Monta a string de conexao usada pelo SQLAlchemy."""
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def resolved_drive_credentials_path(self) -> Path | None:
        """Resolve path relative to SERVER_DIR if needed."""
        if not self.drive_credentials_path:
            return None
        
        # If absolute, return as is
        if self.drive_credentials_path.is_absolute():
            return self.drive_credentials_path
            
        # Try resolving relative to SERVER_DIR (where secrets folder is)
        server_relative = SERVER_DIR / self.drive_credentials_path
        if server_relative.exists():
            return server_relative
            
        # Fallback to default resolution (CWD)
        return self.drive_credentials_path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna uma unica instancia de Settings para toda a aplicacao."""
    return Settings()

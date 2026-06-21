"""
core/config.py
==============
Application Settings & Configuration

WHY THIS FILE EXISTS:
    Instead of hardcoding values like database URLs, secret keys, or app names
    everywhere in the code, we centralize them here. This follows the 
    "12-Factor App" methodology — a best practice for building scalable software.

HOW IT WORKS:
    Pydantic's BaseSettings automatically reads values from your .env file.
    If an environment variable exists, it uses that. Otherwise it falls back
    to the default value defined here.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    All application settings are defined here as class attributes.
    Pydantic automatically validates their types (e.g., ensures PORT is an int).
    """

    # --- Application ---
    APP_NAME: str = Field(default="AI-Powered NOC Platform")
    APP_VERSION: str = Field(default="1.0.0")
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=True)

    # --- Server ---
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)

    # --- Database ---
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/noc_platform_db"
    )
    USE_SQLITE: bool = Field(default=True)

    # --- Security (will be used in Module 2 - Authentication) ---
    SECRET_KEY: str = Field(default="change-this-in-production")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)

    class Config:
        """
        Tells Pydantic WHERE to look for the environment variables.
        It will read the .env file in the backend/ directory.
        """
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Create a single, shared instance of our settings.
# All other files will import THIS object — not the class itself.
# This is the "Singleton" pattern: one shared config object for the whole app.
settings = Settings()

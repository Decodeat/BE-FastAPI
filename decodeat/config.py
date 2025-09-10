"""
Configuration management for the nutrition label API.
Handles environment variables and application settings.
"""
import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Google Cloud Vision API settings
    google_application_credentials: Optional[str] = Field(
        None, 
        env="GOOGLE_APPLICATION_CREDENTIALS",
        description="Path to Google Cloud service account key file"
    )
    
    # Gemini AI settings
    gemini_api_key: str = Field(
        ..., 
        env="GEMINI_API_KEY",
        description="Gemini AI API key"
    )
    
    # API settings
    api_title: str = Field(
        "Nutrition Label Analysis API",
        description="API title"
    )
    api_description: str = Field(
        "FastAPI service for analyzing nutrition labels from food images using Google Cloud Vision and Gemini AI",
        description="API description"
    )
    api_version: str = Field("1.0.0", description="API version")
    
    # Server settings
    host: str = Field("0.0.0.0", description="Server host")
    port: int = Field(8000, description="Server port")
    debug: bool = Field(False, env="DEBUG", description="Debug mode")
    
    # Image processing settings
    max_image_size: int = Field(10 * 1024 * 1024, description="Maximum image size in bytes (10MB)")
    allowed_image_types: list = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp"],
        description="Allowed image MIME types"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class ConfigManager:
    """Configuration manager for the application."""
    
    def __init__(self):
        # Load environment variables from .env file
        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
        load_dotenv(env_path)
        
        self.settings = Settings()
        self._validate_configuration()
    
    def _validate_configuration(self) -> None:
        """Validate required configuration settings."""
        errors = []
        
        # Validate Gemini API key
        if not self.settings.gemini_api_key:
            errors.append("GEMINI_API_KEY environment variable is required")
        
        # Set up Google Cloud credentials if not provided
        if not self.settings.google_application_credentials:
            # Try to use the default gcp-key.json file
            key_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'gcp-key.json'))
            if os.path.exists(key_path):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = key_path
                self.settings.google_application_credentials = key_path
            else:
                errors.append(
                    "GOOGLE_APPLICATION_CREDENTIALS environment variable is required or "
                    "gcp-key.json file must exist in the project root"
                )
        
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors)
            raise ValueError(error_message)
    
    def get_settings(self) -> Settings:
        """Get application settings."""
        return self.settings


# Global configuration instance
config_manager = ConfigManager()
settings = config_manager.get_settings()
from pydantic import BaseSettings
from typing import List

class Settings(BaseSettings):
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27019"
    MONGODB_DB_NAME: str = "portfolio_db"
    
    # Application
    APP_NAME: str = "Portfolio API"
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]
    
    # Admin
    ADMIN_USERNAME: str = "Mr.hacker"
    ADMIN_PASSWORD: str = "Mr.hacker@19"
    
    # Email
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USE_TLS: bool = True
    EMAIL_USERNAME: str = "your_email@gmail.com"
    EMAIL_PASSWORD: str = "your_app_password"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Parse allowed origins from string if loaded from env
if isinstance(settings.ALLOWED_ORIGINS, str):
    settings.ALLOWED_ORIGINS = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")]

# Parse allowed file types from string if loaded from env
if isinstance(settings.ALLOWED_FILE_TYPES, str):
    settings.ALLOWED_FILE_TYPES = [ft.strip() for ft in settings.ALLOWED_FILE_TYPES.split(",")]

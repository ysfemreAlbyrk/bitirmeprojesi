from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    supabase_url: str
    supabase_key: str
    supabase_service_key: str
    
    # AI Configuration
    llm_provider: str = "gemini"  # Options: gemini, ollama
    gemini_api_key: str
    gemini_model: str = "gemini-pro"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"
    
    # MMAudio Configuration
    mmaudio_path: str = "~/mm/MMAudio"
    
    # Image Generation Configuration
    image_generation_model: str = "clipdrop"  # Options: clipdrop, local
    image_generation_path: str = "~/models/sdxl-turbo"
    clipdrop_api_key: str = ""
    
    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    max_file_size: int = 50000000  # 50MB
    
    # Storage
    storage_bucket_name: str = "media-assets"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

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
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    
    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # Logging Configuration
    log_level: str = "INFO"
    log_dir: str = "logs"
    log_max_bytes: int = 10485760  # 10MB
    log_backup_count: int = 5
    
    # Database Connection Pool Configuration
    db_pool_connections: int = 10
    db_pool_maxsize: int = 100
    db_connection_timeout: int = 30
    db_read_timeout: int = 30
    db_write_timeout: int = 30
    
    # Rate Limiting Configuration
    rate_limit_enabled: bool = True
    rate_limit_storage: str = "memory"  # Options: memory, redis
    
    # Celery Configuration
    celery_broker_url: str = ""
    celery_result_backend: str = ""
    celery_worker_concurrency: int = 2
    celery_task_time_limit: int = 1800  # 30 minutes
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields in .env


settings = Settings()

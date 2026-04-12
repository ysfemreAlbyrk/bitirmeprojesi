"""Structured logging configuration for VibeTale backend"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from config import settings


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logger(name: str = "vibetale") -> logging.Logger:
    """
    Set up structured logger with console and file handlers.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        log_dir / f"{name}.log",
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler for errors and critical logs only
    error_handler = RotatingFileHandler(
        log_dir / f"{name}_error.log",
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str = "vibetale") -> logging.Logger:
    """
    Get or create logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Initialize default logger
logger = setup_logger("vibetale")

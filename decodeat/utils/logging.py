"""
Logging utilities for structured logging.
"""
import logging
import sys
from typing import Any, Dict
import json
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class LoggingService:
    """Service for structured logging throughout the application."""
    
    def __init__(self, name: str = "nutrition-label-api"):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Set up the logger with structured formatting."""
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def info(self, message: str, extra_data: Dict[str, Any] = None) -> None:
        """Log info message with optional extra data."""
        self._log(logging.INFO, message, extra_data)
    
    def warning(self, message: str, extra_data: Dict[str, Any] = None) -> None:
        """Log warning message with optional extra data."""
        self._log(logging.WARNING, message, extra_data)
    
    def error(self, message: str, extra_data: Dict[str, Any] = None, exc_info: bool = False) -> None:
        """Log error message with optional extra data and exception info."""
        self._log(logging.ERROR, message, extra_data, exc_info)
    
    def debug(self, message: str, extra_data: Dict[str, Any] = None) -> None:
        """Log debug message with optional extra data."""
        self._log(logging.DEBUG, message, extra_data)
    
    def _log(self, level: int, message: str, extra_data: Dict[str, Any] = None, exc_info: bool = False) -> None:
        """Internal method to log with extra data."""
        extra = {"extra_data": extra_data} if extra_data else {}
        self.logger.log(level, message, extra=extra, exc_info=exc_info)


# Global logging service instance
logger = LoggingService()
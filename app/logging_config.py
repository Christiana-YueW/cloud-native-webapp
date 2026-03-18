"""
Logging configuration for the application.

Configures logging to write to both file and console with appropriate
formatting for CloudWatch collection.
"""
import logging
import sys
import time
from pathlib import Path


def setup_logging() -> logging.Logger:
    """
    Configure application logging.
    
    Logs are written to:
    - /var/log/csye6225/webapp.log (collected by CloudWatch Agent)
    - stdout (for local development)
    
    Returns:
        Logger instance for the application
    """
    # Get logger for this application
    logger = logging.getLogger('csye6225')
    
    # Avoid adding duplicate handlers if called multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    # Log format: timestamp (UTC) - logger name - level - message
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%dT%H:%M:%SZ'  # ISO 8601 format with Z suffix for UTC
    
    # Create formatter with UTC time
    formatter = logging.Formatter(log_format, date_format)
    formatter.converter = time.gmtime  # Force UTC
    
    # File handler - for production (CloudWatch collection)
    log_file = Path('/var/log/csye6225/webapp.log')
    try:
        # Ensure directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (PermissionError, OSError) as e:
        # If we can't write to the log file, log to console only
        print(f"Warning: Could not create log file {log_file}: {e}", file=sys.stderr)
    
    # Console handler - for development and debugging
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False
    
    logger.info("Application logging initialized")
    
    return logger


# Create a module-level logger that can be imported
app_logger = setup_logging()
"""
Logging configuration for the application.

Configures structured JSON logging for CloudWatch collection.
"""
import logging
import sys
import time
import json
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    Outputs each log record as a single-line JSON object.
    """

    def __init__(self):
        super().__init__()
        self.converter = time.gmtime  # Force UTC

    def format(self, record):
        log_object = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.getMessage(),
        }

        skip = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
            'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
            'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
            'thread', 'threadName', 'processName', 'process', 'message',
            'taskName',
        }
        for key, value in record.__dict__.items():
            if key not in skip:
                log_object[key] = value

        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_object)


def setup_logging() -> logging.Logger:
    """
    Configure application logging with JSON format.

    Logs are written to:
    - /var/log/csye6225/webapp.log (collected by CloudWatch Agent)
    - stdout (for local development)

    Returns:
        Logger instance for the application
    """
    logger = logging.getLogger("csye6225")

    # Avoid adding duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = JSONFormatter()

    # File handler - for production (CloudWatch collection)
    log_file = Path("/var/log/csye6225/webapp.log")
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, mode="a")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (PermissionError, OSError) as e:
        print(
            f"Warning: Could not create log file {log_file}: {e}", file=sys.stderr
        )

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
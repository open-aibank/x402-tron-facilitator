
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

def setup_logging(logging_config=None):
    """
    Setup logging configuration.
    
    Args:
        logging_config: Dictionary containing logging configuration.
                       Expected keys: 'dir', 'filename', 'level', 'backup_count'
    """
    # Get root logger
    root_logger = logging.getLogger()
    
    # Set level (default INFO)
    level_str = logging_config.get("level", "INFO").upper() if logging_config else "INFO"
    level = getattr(logging, level_str, logging.INFO)
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates if re-initialized
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File Handler (if config provided)
    if logging_config and logging_config.get("dir") and logging_config.get("filename"):
        log_dir = logging_config.get("dir", "logs")
        filename = logging_config.get("filename", "app.log")
        backup_count = logging_config.get("backup_count", 30)
        
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, filename)
        
        try:
            file_handler = TimedRotatingFileHandler(
                filename=log_path,
                when="midnight",
                interval=1,
                backupCount=backup_count,  # 0 means keep all old log files
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            logging.info(f"File logging enabled: {log_path} (Level: {level_str}, Daily rotation)")
        except Exception as e:
            logging.error(f"Failed to setup file logging: {e}")


import logging
import os
from logging.handlers import RotatingFileHandler

from azure.monitor.opentelemetry import configure_azure_monitor

from comprendo.configuration import app_config

# Configure Azure Monitor if connection string is provided
if app_config.str("APPLICATIONINSIGHTS_CONNECTION_STRING", None):
    print("Configuring Azure Monitor")
    configure_azure_monitor(logger_name="comprendo")

# Configure file logging if LOG_TO_FOLDER is provided
log_folder = app_config.str("LOG_TO_FOLDER", "")
if log_folder and log_folder.strip():
    print(f"Configuring file logging to folder: {log_folder}")
    # Ensure the log directory exists
    os.makedirs(log_folder, exist_ok=True)
    
    # Create a rotating file handler
    log_file_path = os.path.join(log_folder, "comprendo.log")
    file_handler = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=20 * 1024 * 1024,  # 20MB per file
        backupCount=5,  # Keep 5 files max
        encoding="utf-8"
    )
    
    # Use the same formatter as in app_logging.py
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] {req=%(request_id)s,client=%(client_id)s,mock=%(mock_mode)s} - %(message)s"
        )
    )
    
    # Add the filter from app_logging.py
    from comprendo.app_logging import ContextFilter
    file_handler.addFilter(ContextFilter())
    
    # Add the handler to the logger
    logger = logging.getLogger("comprendo")
    logger.addHandler(file_handler)

import logging
import os
import sys
from pythonjsonlogger import jsonlogger

def configure_logging():
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    handler.setFormatter(jsonlogger.JsonFormatter(fmt))
    root = logging.getLogger()
    root.setLevel(level)
    # replace existing handlers to avoid duplicate logs
    root.handlers = [handler]

    # route uvicorn loggers to same handler/level
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = root.handlers
        lg.setLevel(level)
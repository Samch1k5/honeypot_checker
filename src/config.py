# src/config.py

"""
Config module.

This is config for whole project with all needed data
"""

import logging
import os

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
LOG_FILE = "honeypot_checker.log"

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(f"logs/{LOG_FILE}"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("honeypot_checker")

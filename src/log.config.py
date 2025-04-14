import logging.config
from typing import Any

import yaml

with open("config/logging.conf.yml", "r") as f:
    LOGGING_CONFIG: Any = yaml.full_load(f)

logging.config.dictConfig(LOGGING_CONFIG)

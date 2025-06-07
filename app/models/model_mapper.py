from utils.key_manager import ModelCostLevel
from typing import Optional

import json
import logging


logger = logging.getLogger(__name__)


class ModelMapper:
    _instance: Optional['ModelMapper'] = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_file: str = "./model_mapping.json"):
        self.config_file = config_file
        self.model_mapping = {}
        self.default_level = ModelCostLevel.MID

        self.load_config()

    def load_config(self) -> bool:
        try:
            with open(self.config_file, 'r', encoding="utf-8") as f:
                model_mapping = json.load(f)

            for model_name, level_str in model_mapping.items():
                try:
                    level = ModelCostLevel[level_str.upper()]
                    self.model_mapping[model_name.lower()] = level
                except (KeyError, AttributeError):
                    logger.warning(f"Unsupported cost level '{level_str}' for model '{model_name}'")
                    continue

            logger.info(f"Loaded {len(self.model_mapping)} model mappings from {self.config_file}")
            return True
        except Exception as e:
            logger.warning(f"Can't load config file: {e}. Using default mapping.")
            return False
        
    def get_model_cost_level(self, model_name: str) -> ModelCostLevel:
        model_name_lower = model_name.lower().strip()
        if model_name_lower in self.model_mapping:
                    return self.model_mapping[model_name_lower]
        else:
             return self.default_level
from utils.key_manager import ModelCostLevel
from typing import Optional, Dict
from pathlib import Path

import json
import logging
import threading


logger = logging.getLogger(__name__)


class ModelMapper:
    def __init__(self, default_level: ModelCostLevel = ModelCostLevel.MID):
        self.default_level = default_level
        self.model_mapping: Dict[str, ModelCostLevel] = {}
        self._lock = threading.Lock()
        self._config_file: Optional[Path] = None


    def load_config(self, config_file: str | Path) -> bool:
        self._config_file = Path(config_file)

        with self._lock:
            self.model_mapping = {}
            try:
                with self._config_file.open('r', encoding="utf-8") as f:
                    raw_mapping = json.load(f)
                for model_name, level_str in raw_mapping.items():
                    try:
                        level = ModelCostLevel[level_str.upper()]
                        self.model_mapping[model_name.lower()] = level
                    except KeyError:
                        logger.warning(
                            f"Config Error in '{self._config_file}': "
                            f"Unsupported cost level '{level_str}' for model '{model_name}'. Skipping."
                        )
                    
                    logger.info(f"Successfully loaded {len(self.model_mapping)} model mappings from {self._config_file}")
                    return True

            except FileNotFoundError:
                logger.error(f"Configuration file not found: '{self._config_file}'")
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from '{self._config_file}': {e}")
            except Exception as e:
                logger.error(f"An unexpected error occurred while loading config '{self._config_file}': {e}", exc_info=True)
            return False

    def get_model_cost_level(self, model_name: str) -> ModelCostLevel:
        if not self.model_mapping:
            return self.default_level
        model_name_lower = model_name.lower().strip()

        with self._lock:
            return self.model_mapping.get(model_name_lower, self.default_level)
from enum import Enum
from typing import Optional
from typing import List
from pathlib import Path

import redis
import os
import logging


logger = logging.getLogger(__name__)


class KeyManagerError(Exception):
    pass
class KeyNotFoundError(KeyManagerError):
    pass
class RedisConnectionError(KeyManagerError):
    pass


class KeyQuoteLevel(Enum):
    FULL = 1
    MID = 2
    LOW = 3


class ModelCostLevel(Enum):
    FULL = 1
    MID = 2
    LOW = 3


class KeyManager:
    def __init__(self, redis_url: str = None):
        if redis_url is None:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Redis at {redis_url}: {e}")
            raise RedisConnectionError(f"Redis connection failed: {e}") from e

        self.key_prefix = "api_keys:"
        self.queues = {
            level: f"{self.key_prefix}queue:{level.name.lower()}"
            for level in KeyQuoteLevel
        }
        self.processing_queue = f"{self.key_prefix}processing"
        self.key_metadata_hash = f"{self.key_prefix}metadata"

        self.model_to_key_priority = {
            ModelCostLevel.FULL: [KeyQuoteLevel.FULL, KeyQuoteLevel.MID, KeyQuoteLevel.LOW],
            ModelCostLevel.MID: [KeyQuoteLevel.MID, KeyQuoteLevel.FULL, KeyQuoteLevel.LOW],
            ModelCostLevel.LOW: [KeyQuoteLevel.LOW, KeyQuoteLevel.MID, KeyQuoteLevel.FULL]
        }

        self._file_path: Optional[Path] = None

    def _clear_existing_keys(self):
        logger.warning("Clearing all managed API key queues from Redis.")
        keys_to_delete = list(self.queues.values())
        keys_to_delete.append(self.processing_queue)
        keys_to_delete.append(self.key_metadata_hash)
        self.redis_client.delete(*keys_to_delete)

    def load_keys_from_file(
            self, file_path: str | Path,
            level: KeyQuoteLevel = KeyQuoteLevel.FULL
            ):
        self._clear_existing_keys()
        self._file_path = Path(file_path)

        queue_name = self.queues[level]
        
        try:
            with self._file_path.open('r', encoding='utf-8') as f:
                keys_to_add = [
                    line.strip() for line in f
                    if line.strip() and not line.strip().startswith('#')
                ]
                if keys_to_add:
                    pipe = self.redis_client.pipeline()
                    pipe.lpush(queue_name, *keys_to_add)
                    for key in keys_to_add:
                        pipe.hset(self.key_metadata_hash, key, level.name)
                    pipe.execute()
                    logger.info(f"Loaded {len(keys_to_add)} keys into '{level.name}' queue and updated metadata.")
        except FileNotFoundError:
            err_msg = f"Key file not found at '{self._file_path.resolve()}'"
            logger.error(err_msg)
            raise KeyManagerError(err_msg)
        except Exception as e:
            logger.error(f"Error loading keys from file: {e}", exc_info=True)
            raise KeyManagerError(f"Failed to load keys: {e}") from e

    def lease_key(self, model_level: ModelCostLevel) -> str:
        key_priorities: List[KeyQuoteLevel] = self.model_to_key_priority[model_level]
        
        for level in key_priorities:
            source_queue = self.queues[level]
            key = self.redis_client.rpoplpush(source_queue, self.processing_queue)
            if key:
                logger.debug(f"Leased key from level '{level.name}' for model level '{model_level.name}'.")
                return key
        
        logger.warning(f"No available keys for all model level.")
        raise KeyNotFoundError("All key queues are currently empty.")
    
    def release_key(self, key: str, is_exhausted: bool = False):
        removed_count = self.redis_client.lrem(self.processing_queue, 1, key)
        if removed_count == 0:
            logger.warning(f"Attempted to release key '{key}' which was not in the processing queue.")
            return
        
        original_level_str = self.redis_client.hget(self.key_metadata_hash, key)
        if not original_level_str:
            logger.error(f"FATAL: Metadata not found for key '{key}'. Discarding key.")
            return
        
        original_level = KeyQuoteLevel[original_level_str]
        if is_exhausted:
            next_level = self._get_next_level(original_level)
        
        if next_level:
            target_queue = self.queues[next_level]
            self.redis_client.lpush(target_queue, key)
            logger.debug(f"Released key '{key}' back to queue '{next_level.name}'.")
        else:
            self.redis_client.hdel(self.key_metadata_hash, key)
            logger.info(f"Key '{key}' exhausted and permanently removed.")

    def _get_next_level(self, level: KeyQuoteLevel) -> Optional[KeyQuoteLevel]:
        if level == KeyQuoteLevel.FULL: return KeyQuoteLevel.MID
        if level == KeyQuoteLevel.MID: return KeyQuoteLevel.LOW
        return None

    def get_queue_counts(self) -> dict:
        try:
            pipe = self.redis_client.pipeline()
            for queue in self.queues.values():
                pipe.llen(queue)
            counts = pipe.execute()
            return {level.name: count for level, count in zip(KeyQuoteLevel, counts)}
        except redis.exceptions.RedisError as e:
            logger.error(f"Could not get queue counts from Redis: {e}")
            return {level.name: -1 for level in KeyQuoteLevel}
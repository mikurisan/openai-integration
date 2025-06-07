from enum import Enum
from typing import Optional

import redis
import os


class KeyQuoteLevel(Enum):
    FULL = 1
    MID = 2
    LOW = 3


class ModelCostLevel(Enum):
    FULL = 1
    MID = 2
    LOW = 3


class KeyManager:
    _instance: Optional['KeyManager'] = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, redis_url=None):
        if redis_url is None:
            redis_url = os.getenv('REDIS_URL')
        
        if redis_url:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
        else:
            self.redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)

        self.queue_names = {
            KeyQuoteLevel.FULL: "key_queue:full",
            KeyQuoteLevel.MID: "key_queue:mid", 
            KeyQuoteLevel.LOW: "key_queue:low"
        }

        self.model_to_key_mapping = {
            ModelCostLevel.FULL: [KeyQuoteLevel.FULL, KeyQuoteLevel.MID, KeyQuoteLevel.LOW],
            ModelCostLevel.MID: [KeyQuoteLevel.MID, KeyQuoteLevel.FULL, KeyQuoteLevel.LOW],
            ModelCostLevel.LOW: [KeyQuoteLevel.LOW, KeyQuoteLevel.MID, KeyQuoteLevel.FULL]
        }


    def add_key(self, key: str, level: KeyQuoteLevel = KeyQuoteLevel.FULL) -> bool:
        try:
            queue_name = self.queue_names[level]
            self.redis_client.lpush(queue_name, key)
            return True
            
        except Exception as e:
            return False


    def load_keys_from_file(self, file_path: str = "./keys.text", level: KeyQuoteLevel = KeyQuoteLevel.FULL) -> dict:
        if self._initialized:
            return
        self.redis_client.flushall()

        result = {'success': 0, 'failed': 0, 'errors': []}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    key = line.strip()
                    
                    if not key or key.startswith('#'):
                        continue
                    
                    if self.add_key(key, level):
                        result['success'] += 1
                    else:
                        result['failed'] += 1
                        result['errors'].append(f"Line {line_num}: Failed to add key '{key}'")
                        
        except FileNotFoundError:
            result['errors'].append(f"File '{file_path}' not found")
        except Exception as e:
            result['errors'].append(f"Error reading file: {str(e)}")

        self._initialized = True
        return result


    def move_key_next(self, key: str) -> bool:
        try:
            current_level = self._find_key_level(key)

            current_queue = self.queue_names[current_level]
            self.redis_client.lrem(current_queue, 1, key)
            
            next_level = self._get_next_level(current_level)
            if next_level:
                next_queue = self.queue_names[next_level]
                self.redis_client.lpush(next_queue, key)
            
            return True
        
        except Exception as e:
            return False


    def get_key_for_model(self, model_level: ModelCostLevel) -> str:
        try:
            available_key_levels = self.model_to_key_mapping[model_level]
            
            for key_lvel in available_key_levels:
                queue_name = self.queue_names[key_lvel]
                key = self.redis_client.lindex(queue_name, 0)

                if key:
                    if isinstance(key, bytes):
                        key = key.decode("utf-8")
                    return key
                
            return None
        
        except Exception as e:
            return None


    def get_queue_counts(self) -> dict:
        try:
            counts = {}
            for level, queue_name in self.queue_names.items():
                counts[level.name] = self.redis_client.llen(queue_name)
            return counts
        except Exception as e:
            return {level.name: 0 for level in KeyQuoteLevel}


    def _get_next_level(self, current_level: KeyQuoteLevel) -> KeyQuoteLevel:
        level_order = [KeyQuoteLevel.FULL, KeyQuoteLevel.MID, KeyQuoteLevel.LOW]

        try:
            current_index = level_order.index(current_level)
            if current_index < len(level_order) - 1:
                return level_order[current_index + 1]
            else:
                return None
        except ValueError:
            return None


    def test_connection(self):
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            return False
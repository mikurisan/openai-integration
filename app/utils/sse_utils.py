from pydantic import BaseModel
from typing import Any

import json


class SSEFormatter(BaseModel):
    @staticmethod
    def format_reponse(event: str, data: Any) -> str:
        data_json = json.dumps(data) if not isinstance(data, str) else data
        return f"event: {event}\ndata: {data_json}\n\n"
    
    @staticmethod
    def format_chat_completion(data: Any) -> str:
        data_json = json.dumps(data) if not isinstance(data, str) else data
        return f"data: {data_json}\n\n"
from pydantic import BaseModel
from typing import Any

import json


class SSEFormatter(BaseModel):
    @staticmethod
    def format(event: str, data: Any) -> str:
        data_json = json.dumps(data) if not isinstance(data, str) else data
        return f"event: {event}\ndata: {data_json}\n\n"
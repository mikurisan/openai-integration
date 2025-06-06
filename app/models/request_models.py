from pydantic import BaseModel
from typing import List, Optional, Union

class ClientInputContentItem(BaseModel):
    text: str
    type: Optional[str] = None


class ClientMessage(BaseModel):
    role: str
    content: Union[str, List[ClientInputContentItem]]

    def get_text_content(self) -> str:
        if isinstance(self.content, str):
            return self.content
        elif isinstance(self.content, list) and self.content:
            first_item = self.content[0]
            if isinstance(first_item, ClientInputContentItem):
                return first_item.text
            elif isinstance(first_item, dict) and "text" in first_item:
                return first_item.get("text", "")
        return ""


class ChatCompletionClientRequest(BaseModel):
    model: str
    input: List[ClientMessage]
    stream: bool = False
    service_tier: Optional[str] = None
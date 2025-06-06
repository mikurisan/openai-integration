from pydantic import BaseModel, Field
from typing import List, Optional, Union

class ClientInputContentItem(BaseModel):
    text: str
    type: Optional[str] = None


class ClientMessageWithType(BaseModel):
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


class ClientMessage(BaseModel):
    role: str
    content: str


class ClientRequest(BaseModel):
    model: str
    input: List[ClientMessageWithType]
    message: List[ClientMessage] = Field(default_factory=list) 
    stream: bool = False
    service_tier: Optional[str] = None

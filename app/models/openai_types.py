from pydantic import BaseModel, Field
from enum import Enum
from typing import Dict, List, Any, Optional


class ResponseTypes(Enum):
    CREATED = "response.created"
    IN_PROGRESS = "response.in_progress"
    COMPLETED = "response.completed"
    
    OUTPUT_ITEM_ADDED = "response.output_item.added"
    OUTPUT_ITEM_DONE = "response.output_item.done"

    CONTENT_PART_ADDED = "response.content_part.added"
    CONTENT_PART_DONE = "response.content_part.done"

    OUTPUT_TEXT_DELTA = "response.output_text.delta"
    OUTPUT_TEXT_DONE = "response.output_text.done"


class ResponseStatus(Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class CustomBaseModel(BaseModel):
    class Config:
        populate_by_name = True
    
    def to_dict(self) -> Dict[str, Any]:
        return self.dict(by_alias=True)
    

class ResponseBase(CustomBaseModel):
    response_id: str = Field(..., alias="id")
    model_name: str = Field(..., alias="model") 
    created_at: int
    instructions_str: str = Field(..., alias="instructions")
    status: str
    error_obj: Optional[Dict[str, Any]] = Field(None, alias="error")
    output_list: List[Dict[str, Any]] = Field(default_factory=list, alias="output")
    usage_obj: Optional[Dict[str, Any]] = Field(None, alias="usage")
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    
    object: str = "response"
    incomplete_details: None = None
    max_output_tokens: None = None
    parallel_tool_calls: bool = True
    previous_response_id: int = None
    reasoning: Dict[str, None] = Field(default_factory=lambda: {"effort": None, "summary": None})
    store: bool = True
    text: Dict[str, Dict[str, str]] = Field(default_factory=lambda: {"format": {"type": "text"}})
    tool_choice: str = "auto"
    tools: List = Field(default_factory=list)
    truncation: str = "disabled"
    user: None = None
    metadata: Dict = Field(default_factory=dict)


class ItemBase(CustomBaseModel):
    id: str
    type: str
    status: str
    role: str
    content: List[Dict[str, Any]] = Field(default_factory=list)


class OutputItem(CustomBaseModel):
    type: str
    output_index: int = 0
    item: Dict[str, Any]


class PartBase(CustomBaseModel):
    type: str
    text: str = ""
    annotations: List[Dict[str, Any]] = Field(default_factory=list)


class ContentBase(CustomBaseModel):
    type: str
    item_id: str
    output_index: int = 0
    content_index: int = 0


class ContentPart(ContentBase):
    part: Dict[str, Any]


class OutputTextDelta(ContentBase):
    delta: str


class OutputText(ContentBase):
    text: str
    

class ErrorBase(CustomBaseModel):
    type: str
    message: str


class MessageBase(CustomBaseModel):
    content: str = ""
    refusal: None = None
    role: str = "assistant"
    annotations: None = None
    audio: None = None
    function_call: None = None
    tool_calls: None = None


class ChoiceBase(CustomBaseModel):
    finish_reason: str = "stop"
    index: int = 0
    logprobs: None = None
    message: Dict[str, Any] = Field(default_factory=dict)


class ChatCompletionBase(CustomBaseModel):
    response_id: str = Field(..., alias="id")
    choices: List[Dict[str, Any]] = Field(default_factory=list) 
    created_at: int = Field(..., alias="created")
    model_name: str = Field(..., alias="model")
    object: str = "chaht.completion"
    service_tier: str = "default"
    system_fingerprint: str = Field(...)
    usage: Dict[str, Any] = Field(default_factory=dict)

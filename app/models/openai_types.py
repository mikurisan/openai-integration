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
    
    def to_dict(self, exclude: Optional[set] = None) -> Dict[str, Any]:
        return self.model_dump(by_alias=True, exclude=exclude)
    

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
    incomplete_details: Optional[Any] = None
    max_output_tokens: Optional[Any] = None
    parallel_tool_calls: bool = True
    previous_response_id: int = None
    reasoning: Dict[str, None] = Field(default_factory=lambda: {"effort": None, "summary": None})
    store: bool = True
    text: Dict[str, Dict[str, str]] = Field(default_factory=lambda: {"format": {"type": "text"}})
    tool_choice: str = "auto"
    tools: List = Field(default_factory=list)
    truncation: str = "disabled"
    user: Optional[Any] = None
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
    refusal: Optional[str] = None
    role: Optional[str] = None
    annotations: Optional[Any] = None
    audio: Optional[Any] = None
    function_call: Optional[Any] = None
    tool_calls: Optional[Any] = None


class DeltaBase(CustomBaseModel):
    content: Optional[str] = None
    function_call: Optional[Any] = None
    refusal: Optional[Any] = None
    role: Optional[str] = None
    tool_calls: Optional[Any] = None


class ChoiceBase(CustomBaseModel):
    finish_reason: Optional[str] = None
    index: int = 0
    logprobs: Optional[Any] = None


class ChoiceMessage(ChoiceBase):
    message: Dict[str, Any] = Field(default_factory=dict)


class ChoiceDelta(ChoiceBase):
    delta: Dict[str, Any] = Field(default_factory=dict)


class ChatCompletionBase(CustomBaseModel):
    response_id: str = Field(..., alias="id")
    choices: List[Dict[str, Any]] = Field(default_factory=list) 
    created_at: int = Field(..., alias="created")
    model_name: str = Field(..., alias="model")
    object: Optional[str] = "chat.completion"
    service_tier: Optional[str] = "default"
    system_fingerprint: str = Field(...)
    usage: Dict[str, Any] = Field(default_factory=dict)

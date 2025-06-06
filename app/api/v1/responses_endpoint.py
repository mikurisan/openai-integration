from fastapi import APIRouter, HTTPException, Depends
from typing import List
from fastapi import Header
from typing import Optional
from models.request_models import ChatCompletionClientRequest
from dependencies.logging import log_request_body, log_request_header
from fastapi.responses import StreamingResponse, JSONResponse
from services.poe_service import get_poe_response_in_streaming, get_poe_response_none_streaming

import fastapi_poe as fp
import logging

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post(
        "/v1/responses",
        response_model=None,
        dependencies=[
            Depends(log_request_body),
            Depends(log_request_header),
        ]
)
async def create_chat_completion(
    request_data: ChatCompletionClientRequest,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="x-api-key")
):
    poe_api_key = x_api_key
    if authorization and authorization.lower().startswith("bearer "):
        poe_api_key = authorization.split(" ", 1)[1] 
    if not poe_api_key:
        raise HTTPException(
            status_code=401, detail="API key not found in 'Authorization' or 'X-Api-Key' header.")
    
    poe_bot_name = request_data.model
    protocol_messages: List[fp.ProtocolMessage] = []
    instructions_str = "You are a helpful assistant."

    for msg in request_data.input:
        text_content = msg.get_text_content()
        poe_role = msg.role

        if msg.role == "system":
            instructions_str = text_content
        if msg.role == "assistant":
            poe_role = "bot"
        elif msg.role not in ["system", "user", "bot"]:
            logger.warning(f"Warning: Unknown role '{msg.role}', defaulting to 'user'.")
            poe_role = "user"

        protocol_messages.append(fp.ProtocolMessage(
            role=poe_role, content=text_content))

    if not protocol_messages:
        raise HTTPException(
            status_code=400, detail="Messages list (derived from 'input') cannot be empty.")
    
    if request_data.stream:
        return StreamingResponse(
            get_poe_response_in_streaming(
                bot_name=poe_bot_name,
                poe_api_key=poe_api_key,
                protocol_messages=protocol_messages,
                instructions_str=instructions_str,
                request_model_name=request_data.model,
            ),
            media_type="text/event-stream"
        )
    else:
        response = await get_poe_response_none_streaming(
            bot_name=poe_bot_name,
            poe_api_key=poe_api_key,
            protocol_messages=protocol_messages,
            instructions_str=instructions_str,
            request_model_name=request_data.model,
            )
        return JSONResponse(response)
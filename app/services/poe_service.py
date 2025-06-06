from typing import List
from utils.sse_utils import SSEFormatter
from models.openai_types import ResponseStatus, ResponseTypes, ResponseBase
from models.openai_types import ItemBase, OutputItem, PartBase, ContentPart
from models.openai_types import OutputTextDelta, OutputText, ErrorBase
from fastapi_poe.client import BotError

import fastapi_poe as fp
import uuid
import time
import asyncio
import logging
import json


logger = logging.getLogger(__name__)


DEFAULT_SUCCESS_USAGE = {
    "input_tokens": 37, "output_tokens": 11,
    "output_tokens_details": {"reasoning_tokens": 0}, "total_tokens": 48
}
DEFAULT_ERROR_USAGE = {
    "input_tokens": 0, "output_tokens": 0,
    "output_tokens_details": {"reasoning_tokens": 0}, "total_tokens": 0
}


async def get_poe_response_in_streaming(
        bot_name: str, poe_api_key: str,
        protocol_messages: List[fp.ProtocolMessage],
        instructions_str: str,
        request_model_name: str,
):
    temp, top_p_val = 1.0, 1.0

    response_id = f"resp-{uuid.uuid4().hex}"
    created_at = int(time.time())
    base_response_args = {
        "response_id": response_id, "model_name": request_model_name,
        "created_at": created_at, "instructions_str": instructions_str,
        "temperature": temp, "top_p": top_p_val
    }

    sse_formatter = SSEFormatter()
    try:
        created_payload = ResponseBase(**base_response_args, status=ResponseStatus.IN_PROGRESS.value)
        yield sse_formatter.format(ResponseTypes.CREATED.value, {'type': ResponseTypes.CREATED.value, 'response': created_payload.to_dict()})
        await asyncio.sleep(0.01)

        in_progress_payload = ResponseBase(**base_response_args, status=ResponseStatus.IN_PROGRESS.value)
        yield sse_formatter.format(ResponseTypes.CREATED.value, {'type': ResponseTypes.IN_PROGRESS.value, 'response': in_progress_payload.to_dict()})
        await asyncio.sleep(0.01)

        item_id = f"msg-{uuid.uuid4().hex}"
        item_base_payload = ItemBase(
            id=item_id, type="message",
            status=ResponseStatus.IN_PROGRESS.value,
            role="assistant"
            )
        output_item_added_payload = OutputItem(type=ResponseTypes.OUTPUT_ITEM_ADDED.value, item=item_base_payload.to_dict())
        yield sse_formatter.format(ResponseTypes.OUTPUT_ITEM_ADDED.value, output_item_added_payload.to_dict())
        await asyncio.sleep(0.01)

        part_base_payload = PartBase(type="output_text")
        content_part_payload = ContentPart(
            type=ResponseTypes.CONTENT_PART_ADDED.value,
            item_id=item_id,
            part=part_base_payload.to_dict()
            )
        yield sse_formatter.format(ResponseTypes.CONTENT_PART_ADDED.value, content_part_payload.to_dict())
        await asyncio.sleep(0.01)
        
        accumulated_text = ""
        async for partial in fp.get_bot_response(
            messages=protocol_messages, bot_name=bot_name, api_key=poe_api_key
        ):
            if isinstance(partial, fp.PartialResponse) and partial.text:
                accumulated_text += partial.text
                delta_data = OutputTextDelta(
                    type=ResponseTypes.OUTPUT_TEXT_DELTA.value,
                    item_id=item_id,
                    delta=partial.text
                )
                yield sse_formatter.format(ResponseTypes.OUTPUT_TEXT_DELTA.value, delta_data.to_dict())
                await asyncio.sleep(0.01)
            elif isinstance(partial, fp.ErrorResponse):
                error_text_from_poe = f"Poe ErrorResponse: {partial.text} (Code: {partial.error_code}, Type: {partial.error_type})"
                logger.error(error_text_from_poe)
                error_obj_payload = ErrorBase(
                    type=str(partial.error_type) if partial.error_type else "upstream_error",
                    message=partial.text or "Unknown error from Poe ErrorResponse"
                    )
                completed_error_payload = ResponseBase(
                    **base_response_args,
                    status="failed",
                    error_obj=error_obj_payload.to_dict(),
                    usage_obj=DEFAULT_ERROR_USAGE
                    )
                yield sse_formatter.format(ResponseTypes.COMPLETED.value, {'type': ResponseTypes.COMPLETED.value, 'response': completed_error_payload.to_dict()})
                return

        output_text_done_payload = OutputText(
            type=ResponseTypes.OUTPUT_TEXT_DONE.value,
            item_id=item_id, text=accumulated_text
            )
        yield sse_formatter.format(ResponseTypes.OUTPUT_TEXT_DONE.value, output_text_done_payload.to_dict())
        await asyncio.sleep(0.01)

        part_base_payload = PartBase(type="output_text", text=accumulated_text)
        content_part_done_payload = ContentPart(
            type=ResponseTypes.CONTENT_PART_DONE.value,
            item_id=item_id,
            part=part_base_payload.to_dict()
        )
        yield sse_formatter.format(ResponseTypes.CONTENT_PART_DONE.value, content_part_done_payload.to_dict())
        await asyncio.sleep(0.01)

        item_base_payload = ItemBase(
            id=item_id, type="message",
            status=ResponseStatus.COMPLETED.value,
            role="assistant",
            content= [part_base_payload.to_dict()]
            )
        output_item_done_payload = OutputItem(
            type=ResponseTypes.OUTPUT_ITEM_DONE.value,
            item=item_base_payload.to_dict()
            )
        yield sse_formatter.format(ResponseTypes.OUTPUT_ITEM_DONE.value, output_item_done_payload.to_dict())
        await asyncio.sleep(0.01)

        response_completed_payload = ResponseBase(
            **base_response_args, status=ResponseStatus.COMPLETED.value,
            output_list=[item_base_payload.to_dict()], usage_obj=DEFAULT_SUCCESS_USAGE
        )
        yield sse_formatter.format(ResponseTypes.COMPLETED.value, {'type': ResponseTypes.COMPLETED.value, 'response': response_completed_payload.to_dict()})
    
    except BotError as e:
        logger.error(f"Handling BotError from Poe: {str(e)}")

        error_message_detail = "Internal server error from Poe."
        poe_error_type = "bot_error"

        if e.args and isinstance(e.args[0], str):
            try:
                error_data_dict = json.loads(e.args[0])
                error_message_detail = error_data_dict.get(
                    "text", error_message_detail)
            except json.JSONDecodeError:
                logger.error(f"Could not parse BotError JSON content: {e.args[0]}")
                if len(e.args[0]) < 200:
                    error_message_detail = e.args[0]

        logger.error(f"Formatted Poe BotError for client: {error_message_detail}")

        error_obj_payload = ErrorBase(type=poe_error_type, message=error_message_detail)
        completed_error_payload = ResponseBase(
                    **base_response_args,
                    status="failed",
                    error_obj=error_obj_payload.to_dict(),
                    usage_obj=DEFAULT_ERROR_USAGE
                    )
        yield sse_formatter.format(ResponseTypes.COMPLETED.value, {'type': ResponseTypes.COMPLETED.value, 'response': completed_error_payload.to_dict()})

    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        logger.error(
            f"An unexpected error occurred during streaming: {str(e)}\n{tb_str}")
        error_obj_payload = ErrorBase(
            type="internal_server_error",
            message=f"An unexpected error occurred in the adapter: {str(e)}"
            )
        completed_error_payload = ResponseBase(
                    **base_response_args,
                    status="failed",
                    error_obj=error_obj_payload.to_dict(),
                    usage_obj=DEFAULT_ERROR_USAGE
                    )
        yield sse_formatter.format(ResponseTypes.COMPLETED.value, {'type': ResponseTypes.COMPLETED.value, 'response': completed_error_payload.to_dict()})


async def get_poe_response_none_streaming(
        bot_name: str, poe_api_key: str,
        protocol_messages: List[fp.ProtocolMessage],
        instructions_str: str,
        request_model_name: str
):
    temp, top_p_val = 1.0, 1.0

    response_id = f"resp-{uuid.uuid4().hex}"
    created_at = int(time.time())
    base_response_args = {
        "response_id": response_id, "model_name": request_model_name,
        "created_at": created_at, "instructions_str": instructions_str,
        "temperature": temp, "top_p": top_p_val
    }
    accumulated_text = ""
    async for partial in fp.get_bot_response(
        messages=protocol_messages, bot_name=bot_name, api_key=poe_api_key
    ):
        if isinstance(partial, fp.PartialResponse) and partial.text:
            accumulated_text += partial.text
            
        elif isinstance(partial, fp.ErrorResponse):
            error_text_from_poe = f"Poe ErrorResponse: {partial.text} (Code: {partial.error_code}, Type: {partial.error_type})"
            logger.error(error_text_from_poe)
            error_obj_payload = ErrorBase(
                type=str(partial.error_type) if partial.error_type else "upstream_error",
                message=partial.text or "Unknown error from Poe ErrorResponse"
                )
            completed_error_payload = ResponseBase(
                **base_response_args,
                status="failed",
                error_obj=error_obj_payload.to_dict(),
                usage_obj=DEFAULT_ERROR_USAGE
                )
            return completed_error_payload.to_dict()
        
    item_id = f"msg-{uuid.uuid4().hex}"
    part_base_payload = PartBase(type="output_text", text=accumulated_text)
    item_base_payload = ItemBase(
        id=item_id, type="message",
        status=ResponseStatus.COMPLETED.value,
        role="assistant",
        content= [part_base_payload.to_dict()]
        )
    response_completed_payload = ResponseBase(
        **base_response_args, status=ResponseStatus.COMPLETED.value,
        output_list=[item_base_payload.to_dict()], usage_obj=DEFAULT_SUCCESS_USAGE
        )
    return response_completed_payload.to_dict()
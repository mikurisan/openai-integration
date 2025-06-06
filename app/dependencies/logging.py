import logging
from fastapi import Request


logger = logging.getLogger(__name__)


async def log_request_body(request: Request) -> Request:
    try:
        body = await request.body()
        if body:
            logger.info(f"[{request.method} {request.url.path}] Request Body:\n {body.decode('utf-8')}")
        else:
            logger.info(f"[{request.method} {request.url.path}] Empty request body")
    except Exception as e:
        logger.error(f"[{request.method} {request.url.path}] Failed to log request body: {e}")
    

async def log_request_header(request: Request) -> Request:
    logger.info(f"[{request.url.path}] Headers: {dict(request.headers)}")

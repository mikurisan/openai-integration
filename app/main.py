from fastapi import FastAPI, Request
from api.v1.responses_endpoint import router as responses_router
from contextlib import asynccontextmanager
from utils.key_manager import KeyManager
from models.model_mapper import ModelMapper

import uvicorn
import logging
import sys


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing KeyManager...")
    try:
        key_manager = KeyManager()
        result = key_manager.load_keys_from_file()
        logger.info(result)
        if key_manager.test_connection():
            logger.info("KeyManager initialized and Redis connection verified")
        else:
            raise Exception("Redis connection test failed")
    except Exception as e:
        logger.error(f"Failed to initialize KeyManager: {e}")
        raise

    try:
        logger.info("Initializing ModelMapper...")
        model_mapper = ModelMapper()
        logger.info("ModelMapper initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize ModelMapper: {e}")
        raise
    
    logger.info("All components initialized successfully")
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(responses_router)


@app.get("/")
@app.head("/")
async def root():
    return {"message": "API is running", "endpoint": "/v1/responses"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=2026)
from fastapi import FastAPI
from api.v1.responses_endpoint import router as responses_router
from contextlib import asynccontextmanager
from utils.key_manager import KeyManager
from models.model_mapper import ModelMapper
from pathlib import Path

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
async def create_instance(app: FastAPI):
    logger.info("Initializing singleton instances...")
    key_manager_instance = KeyManager()
    key_manager_instance.load_keys_from_file(Path(__file__).parent / "keys.text")

    model_mapper_instance = ModelMapper()
    model_mapper_instance.load_config(Path(__file__).parent / "model_mapping.text")

    app.state.key_manager = key_manager_instance
    app.state.model_mapper = model_mapper_instance

    logger.info("Singleton instances for KeyManager and ModelMapper are created and loaded.")
    yield


app = FastAPI(lifespan=create_instance)
app.include_router(responses_router)


@app.get("/")
@app.head("/")
async def root():
    return {"message": "API is running", "endpoint": "/"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=2026)
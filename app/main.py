from fastapi import FastAPI, Request
from api.v1.responses_endpoint import router as responses_router

import uvicorn
import logging
import sys


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)


app = FastAPI()
app.include_router(responses_router)


@app.get("/")
@app.head("/")
async def root():
    return {"message": "API is running", "endpoint": "/v1/responses"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=2026)
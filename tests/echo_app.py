import os

import asyncio
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse


PORT = int(os.getenv("PORT", 9001))

app = FastAPI()


@app.get("/")
async def root():
    return {
        "message": "hello from upstream",
        "port": PORT,
    }


@app.api_route(
    "/echo",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def echo(request: Request):
    body = await request.body()

    return {
        "method": request.method,
        "path": request.url.path,
        "headers": dict(request.headers),
        "body": body.decode(errors="replace"),
        "port": PORT,
    }


@app.get("/slow")
async def slow(delay: float = 5):
    await asyncio.sleep(delay)

    return {
        "message": "slow response",
        "delay": delay,
        "port": PORT,
    }


@app.get("/stream")
async def stream():
    async def generator():
        for i in range(5):
            yield f"chunk-{i}\n"

            await asyncio.sleep(0.5)

    return StreamingResponse(
        generator(),
        media_type="text/plain",
    )


@app.get("/big")
async def big(size_mb: int = 10):
    data = b"x" * 1024 * 1024 * size_mb

    return {
        "size_mb": size_mb,
        "data": data.decode(),
        "port": PORT,
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=PORT,
        reload=False,
        workers=1,
        # timeout_keep_alive=60, TODO: will be implemented when proxy will be able to handle keep-alive
    )

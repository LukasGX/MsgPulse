import asyncio
import json
import re

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from bot import start_bot, stop_bot

app = FastAPI()

STREAM_REGEX = re.compile(r"^\[SET_STREAM\] .*$")

app.mount("/f", StaticFiles(directory="static"), name="static")

STOP_TASKS = {}


@app.get("/")
async def root():
    return FileResponse("index.html")

async def delayed_stop(bot):
    # wait 5 min
    await asyncio.sleep(300)

    # no clients connected in the meantime
    if len(bot.clients) == 0:
        await stop_bot(bot.stream)

        STOP_TASKS.pop(bot.stream, None)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    bot = None

    try:
        while True:
            data = await websocket.receive_text()

            if not data.strip():
                raise HTTPException(
                    status_code=400,
                    detail="Message cannot be empty"
                )

            if STREAM_REGEX.match(data):
                stream_name = data.split(" ", 1)[1]

                bot = await start_bot(stream_name)
                if not bot:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Stream not found or offline: {stream_name}"
                    )
                
                await websocket.send_text(
                    json.dumps({
                        "type": "live_info",
                        "live_since": bot.live_since.isoformat()
                    })
                )

                # register ws
                bot.clients.add(websocket)

                await websocket.send_text(
                    json.dumps({
                        "type": "info",
                        "msg": f"Connected to stream: {stream_name}"
                    })
                )

            else:
                await websocket.send_text(
                    f"Invalid msg: {data}"
                )

    except WebSocketDisconnect:
        if bot:
            bot.clients.discard(websocket)

            if len(bot.clients) == 0:
                STOP_TASKS[bot.stream] = asyncio.create_task(
                    delayed_stop(bot)
                )

    except HTTPException as e:
        await websocket.send_text(
            f"Error {e.status_code}: {e.detail}"
        )
        await websocket.close()

@app.get("/all-words/{streamer}")
async def all_words(streamer: str):
    bot = await start_bot(streamer)
    if not bot:
        raise HTTPException(
            status_code=404,
            detail=f"No bot found for streamer: {streamer}"
        )
    return {
        "words": bot.getAllWords()
    }
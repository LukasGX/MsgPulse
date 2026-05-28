import re

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from bot import start_bot, stop_bot

app = FastAPI()

STREAM_REGEX = re.compile(r"^\[SET_STREAM\] .*$")

app.mount("/f", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("index.html")


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

                # websocket registrieren
                bot.clients.add(websocket)

                await websocket.send_text(
                    f"Connected to stream: {stream_name}"
                )

            else:
                await websocket.send_text(
                    f"Invalid msg: {data}"
                )

    except WebSocketDisconnect:
        if bot:
            bot.clients.discard(websocket)

            # optional:
            # wenn niemand mehr verbunden ist -> bot stoppen
            if len(bot.clients) == 0:
                await stop_bot(bot.stream)

    except HTTPException as e:
        await websocket.send_text(
            f"Error {e.status_code}: {e.detail}"
        )
        await websocket.close()
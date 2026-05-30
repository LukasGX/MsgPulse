import asyncio
import json
import re
import os
import secrets

from fastapi import Depends, FastAPI, Form, Request, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from bot import start_bot, stop_bot

app = FastAPI()

SESSIONS = set()

APP_USERNAME = os.getenv("APP_USERNAME")
APP_PASSWORD = os.getenv("APP_PASSWORD")

STREAM_REGEX = re.compile(r"^\[SET_STREAM\] .*$")

app.mount("/f", StaticFiles(directory="static"), name="static")

STOP_TASKS = {}

def get_user(request: Request):
    token = request.cookies.get("session")

    if not token or token not in SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    return token

@app.get("/")
async def root(user=Depends(get_user)):
    return FileResponse("index.html")

@app.get("/login")
async def login_page():
    return FileResponse("login.html")

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if username == APP_USERNAME and password == APP_PASSWORD:
        token = secrets.token_hex(32)
        SESSIONS.add(token)

        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            key="session",
            value=token,
            httponly=True,
            secure=False,
            samesite="lax"
        )
        return response

    return HTMLResponse("Invalid login", status_code=403)

async def delayed_stop(bot):
    # wait 15 min
    await asyncio.sleep(900)

    # no clients connected in the meantime
    if len(bot.clients) == 0:
        await stop_bot(bot.stream)

        STOP_TASKS.pop(bot.stream, None)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.cookies.get("session")

    if not token or token not in SESSIONS:
        await websocket.close(code=1008)
        return

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
async def all_words(streamer: str, user=Depends(get_user)):
    bot = await start_bot(streamer)
    if not bot:
        raise HTTPException(
            status_code=404,
            detail=f"No bot found for streamer: {streamer}"
        )
    return {
        "words": bot.getAllWords()
    }

@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get("session")
    if token:
        SESSIONS.discard(token)

    response = RedirectResponse("/login")
    response.delete_cookie("session")
    return response
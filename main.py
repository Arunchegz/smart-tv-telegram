import os
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from pyrofork import Client
from stremio import Addon # pip install stremio

# 1. Setup Telegram Client
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

tg_app = Client("stremio_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# 2. Setup Stremio Addon
manifest = {
    "id": "org.telegram.mybridge",
    "name": "My Telegram Stremio",
    "description": "Stream your Telegram files in Stremio",
    "version": "1.0.0",
    "resources": ["stream"],
    "types": ["movie", "series"],
    "idPrefixes": ["tg"] # We will use 'tg:' prefix for IDs
}

addon = Addon(manifest)
app = FastAPI()

# 3. The Streaming logic (The Bridge)
async def tg_stream_generator(chat_id, message_id):
    async with tg_app:
        message = await tg_app.get_messages(int(chat_id), int(message_id))
        file = message.video or message.document
        async for chunk in tg_app.stream_media(file):
            yield chunk

# 4. Stremio Route: /stream/{type}/{id}.json
@app.get("/stream/{type}/{id}.json")
async def get_streams(type: str, id: str):
    # Example ID format: tg:CHATID:MESSAGEID
    _, chat_id, msg_id = id.split(":")
    stream_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/play/{chat_id}/{msg_id}"
    
    return {
        "streams": [{
            "title": "Telegram High Speed",
            "url": stream_url
        }]
    }

# 5. Direct Playback Route
@app.get("/play/{chat_id}/{msg_id}")
async def play_video(chat_id: str, msg_id: str):
    return StreamingResponse(tg_stream_generator(chat_id, msg_id), media_type="video/mp4")

# Wrap Stremio addon into FastAPI
app.mount("/", addon.app)

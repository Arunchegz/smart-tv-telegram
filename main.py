import os
import mimetypes
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from pyrofork import Client
from stremio import Addon

# --- 1. CONFIGURATION ---
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

# Initialize Telegram Client
tg_app = Client("stremio_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# --- 2. STREMIO MANIFEST ---
manifest = {
    "id": "org.telegram.bridge",
    "name": "Telegram Cloud Streamer",
    "description": "Stream Telegram videos directly in Stremio",
    "version": "1.0.0",
    "resources": ["stream"],
    "types": ["movie", "series"],
    "idPrefixes": ["tg"]
}

addon = Addon(manifest)
app = FastAPI()

# --- 3. STREAMING BRIDGE LOGIC ---
async def tg_stream_generator(chat_id: int, message_id: int, offset: int = 0):
    async with tg_app:
        message = await tg_app.get_messages(chat_id, message_id)
        file = message.video or message.document
        
        # Stream from specific offset for seeking support
        async for chunk in tg_app.stream_media(file, offset=offset):
            yield chunk

# --- 4. ROUTES ---

@addon.stream()
async def stream_handler(args):
    # args.id format: tg:CHATID:MSGID
    try:
        _, chat_id, msg_id = args.id.split(":")
        # Generate the link back to our own /play route
        base_url = os.getenv("RENDER_EXTERNAL_URL") or "http://localhost:10000"
        play_url = f"{base_url}/play/{chat_id}/{msg_id}"
        
        return {"streams": [{"title": "🚀 Telegram High-Speed", "url": play_url}]}
    except:
        return {"streams": []}

@app.get("/play/{chat_id}/{msg_id}")
async def play_video(chat_id: int, msg_id: int, request: Request):
    # Simple streaming response (Range requests can be added for better seeking)
    return StreamingResponse(
        tg_stream_generator(chat_id, msg_id), 
        media_type="video/mp4"
    )

# Mount the Stremio addon routes to FastAPI
app.mount("/", addon.app)

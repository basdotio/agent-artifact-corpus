"""
FastAPI HTTP bridge for Telegram functionality.
Exposes the existing Telethon client via REST API for the TypeScript agent.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Union, Any
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.tl.types import User, Chat, Channel

load_dotenv()

TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME")
SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING")

# Global client instance
client: TelegramClient = None


def json_serializer(obj):
    """Helper function to convert non-serializable objects for JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def format_entity(entity) -> Dict[str, Any]:
    """Format entity information consistently."""
    result = {"id": entity.id}
    if isinstance(entity, User):
        result["type"] = "user"
        result["first_name"] = getattr(entity, "first_name", None)
        result["last_name"] = getattr(entity, "last_name", None)
        result["username"] = getattr(entity, "username", None)
        result["phone"] = getattr(entity, "phone", None)
    elif isinstance(entity, Chat):
        result["type"] = "chat"
        result["title"] = getattr(entity, "title", None)
    elif isinstance(entity, Channel):
        result["type"] = "channel"
        result["title"] = getattr(entity, "title", None)
        result["username"] = getattr(entity, "username", None)
    return result


def format_message(message) -> Dict[str, Any]:
    """Format message information consistently."""
    result = {
        "id": message.id,
        "date": message.date.isoformat() if message.date else None,
        "text": message.message,
        "out": message.out,  # True if sent by us
    }
    
    # Sender info
    if message.sender:
        if hasattr(message.sender, "first_name"):
            first = getattr(message.sender, "first_name", "") or ""
            last = getattr(message.sender, "last_name", "") or ""
            result["sender_name"] = f"{first} {last}".strip() or "Unknown"
        elif hasattr(message.sender, "title"):
            result["sender_name"] = message.sender.title
        else:
            result["sender_name"] = "Unknown"
        result["sender_id"] = message.sender.id
    else:
        result["sender_name"] = "Unknown"
        result["sender_id"] = None
    
    # Reply info
    if message.reply_to and message.reply_to.reply_to_msg_id:
        result["reply_to_msg_id"] = message.reply_to.reply_to_msg_id
    
    # Media info
    if message.media:
        result["has_media"] = True
        result["media_type"] = type(message.media).__name__
    else:
        result["has_media"] = False
    
    return result


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage Telegram client lifecycle."""
    global client
    
    if SESSION_STRING:
        client = TelegramClient(StringSession(SESSION_STRING), TELEGRAM_API_ID, TELEGRAM_API_HASH)
    else:
        client = TelegramClient(TELEGRAM_SESSION_NAME, TELEGRAM_API_ID, TELEGRAM_API_HASH)
    
    await client.start()
    print("✅ Telegram client connected")
    
    yield
    
    await client.disconnect()
    print("👋 Telegram client disconnected")


app = FastAPI(
    title="Telegram API Bridge",
    description="HTTP API for Telegram operations",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class SendMessageRequest(BaseModel):
    message: str
    reply_to: Optional[int] = None


class ScheduleMessageRequest(BaseModel):
    message: str
    minutes_from_now: int


class SendFileRequest(BaseModel):
    caption: Optional[str] = None


# Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "connected": client.is_connected() if client else False}


@app.get("/me")
async def get_me():
    """Get current user info."""
    try:
        me = await client.get_me()
        return format_entity(me)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chats")
async def get_chats(
    limit: int = Query(default=50, le=200),
    chat_type: Optional[str] = Query(default=None, description="Filter by type: user, chat, channel")
):
    """Get list of chats/dialogs."""
    try:
        dialogs = await client.get_dialogs(limit=limit)
        chats = []
        
        for dialog in dialogs:
            entity = dialog.entity
            chat_info = format_entity(entity)
            chat_info["unread_count"] = dialog.unread_count
            chat_info["last_message"] = dialog.message.message[:100] if dialog.message and dialog.message.message else None
            
            # Filter by type if specified
            if chat_type:
                if chat_type == "user" and isinstance(entity, User):
                    chats.append(chat_info)
                elif chat_type == "chat" and isinstance(entity, Chat):
                    chats.append(chat_info)
                elif chat_type == "channel" and isinstance(entity, Channel):
                    chats.append(chat_info)
            else:
                chats.append(chat_info)
        
        return {"chats": chats, "count": len(chats)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chats/{chat_id}")
async def get_chat(chat_id: Union[int, str]):
    """Get detailed info about a specific chat."""
    try:
        # Handle string chat_id (username)
        if isinstance(chat_id, str) and not chat_id.lstrip('-').isdigit():
            entity = await client.get_entity(chat_id)
        else:
            entity = await client.get_entity(int(chat_id))
        
        return format_entity(entity)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chats/{chat_id}/messages")
async def get_messages(
    chat_id: Union[int, str],
    limit: int = Query(default=20, le=100),
    offset_id: Optional[int] = Query(default=None, description="Get messages before this ID")
):
    """Get messages from a chat."""
    try:
        # Handle string chat_id (username)
        if isinstance(chat_id, str) and not chat_id.lstrip('-').isdigit():
            entity = await client.get_entity(chat_id)
        else:
            entity = await client.get_entity(int(chat_id))
        
        kwargs = {"limit": limit}
        if offset_id:
            kwargs["offset_id"] = offset_id
        
        messages = await client.get_messages(entity, **kwargs)
        
        return {
            "messages": [format_message(msg) for msg in messages],
            "count": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chats/{chat_id}/messages")
async def send_message(chat_id: Union[int, str], request: SendMessageRequest):
    """Send a message to a chat."""
    try:
        # Handle string chat_id (username)
        if isinstance(chat_id, str) and not chat_id.lstrip('-').isdigit():
            entity = await client.get_entity(chat_id)
        else:
            entity = await client.get_entity(int(chat_id))
        
        kwargs = {}
        if request.reply_to:
            kwargs["reply_to"] = request.reply_to
        
        result = await client.send_message(entity, request.message, **kwargs)
        
        return {
            "success": True,
            "message_id": result.id,
            "date": result.date.isoformat() if result.date else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chats/{chat_id}/schedule")
async def schedule_message(chat_id: Union[int, str], request: ScheduleMessageRequest):
    """Schedule a message to be sent at a future time."""
    from datetime import timedelta

    try:
        if request.minutes_from_now < 1:
            raise HTTPException(status_code=400, detail="minutes_from_now must be at least 1")
        if request.minutes_from_now > 525600:
            raise HTTPException(status_code=400, detail="minutes_from_now cannot exceed 525600 (1 year)")

        # Handle string chat_id (username)
        if isinstance(chat_id, str) and not chat_id.lstrip('-').isdigit():
            entity = await client.get_entity(chat_id)
        else:
            entity = await client.get_entity(int(chat_id))

        schedule_time = datetime.now() + timedelta(minutes=request.minutes_from_now)
        result = await client.send_message(entity, request.message, schedule=schedule_time)

        return {
            "success": True,
            "message_id": result.id,
            "scheduled_for": schedule_time.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chats/{chat_id}/files")
async def send_file(
    chat_id: Union[int, str],
    file: UploadFile = File(...),
    caption: Optional[str] = Form(default=None),
    voice_note: bool = Form(default=False)
):
    """Send a file (photo, document, or voice note) to a chat."""
    try:
        # Handle string chat_id (username)
        if isinstance(chat_id, str) and not chat_id.lstrip('-').isdigit():
            entity = await client.get_entity(chat_id)
        else:
            entity = await client.get_entity(int(chat_id))
        
        # Read file content
        content = await file.read()
        
        # Save temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            result = await client.send_file(
                entity,
                tmp_path,
                caption=caption,
                voice_note=voice_note
            )
            
            return {
                "success": True,
                "message_id": result.id,
                "date": result.date.isoformat() if result.date else None
            }
        finally:
            # Clean up temp file
            import os
            os.unlink(tmp_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/contacts")
async def get_contacts():
    """Get all contacts."""
    try:
        result = await client(functions.contacts.GetContactsRequest(hash=0))
        contacts = []
        
        for user in result.users:
            contacts.append({
                "id": user.id,
                "first_name": getattr(user, "first_name", None),
                "last_name": getattr(user, "last_name", None),
                "username": getattr(user, "username", None),
                "phone": getattr(user, "phone", None),
            })
        
        return {"contacts": contacts, "count": len(contacts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/contacts/search")
async def search_contacts(query: str = Query(..., min_length=1)):
    """Search contacts by name, username, or phone."""
    try:
        result = await client(functions.contacts.SearchRequest(q=query, limit=20))
        contacts = []
        
        for user in result.users:
            if isinstance(user, User):
                contacts.append({
                    "id": user.id,
                    "first_name": getattr(user, "first_name", None),
                    "last_name": getattr(user, "last_name", None),
                    "username": getattr(user, "username", None),
                    "phone": getattr(user, "phone", None),
                })
        
        return {"contacts": contacts, "count": len(contacts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= NEW ENDPOINTS =============

class ReactionRequest(BaseModel):
    emoji: str
    big: bool = False


class EditMessageRequest(BaseModel):
    new_text: str


@app.get("/chats/{chat_id}/history")
async def get_history(chat_id: Union[int, str], limit: int = Query(default=100, le=500)):
    """Get full chat history."""
    try:
        if isinstance(chat_id, str) and not chat_id.lstrip('-').isdigit():
            entity = await client.get_entity(chat_id)
        else:
            entity = await client.get_entity(int(chat_id))
        
        messages = await client.get_messages(entity, limit=limit)
        return {
            "messages": [format_message(msg) for msg in messages],
            "count": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chats/{chat_id}/messages/{message_id}/reaction")
async def send_reaction(chat_id: Union[int, str], message_id: int, request: ReactionRequest):
    """Send a reaction to a message."""
    try:
        from telethon.tl.types import ReactionEmoji
        
        if isinstance(chat_id, str) and not chat_id.lstrip('-').isdigit():
            entity = await client.get_entity(chat_id)
        else:
            entity = await client.get_entity(int(chat_id))
        
        await client(functions.messages.SendReactionRequest(
            peer=entity,
            msg_id=message_id,
            big=request.big,
            reaction=[ReactionEmoji(emoticon=request.emoji)]
        ))
        
        return {"success": True, "emoji": request.emoji}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chats/{chat_id}/messages/{message_id}/reply")
async def reply_to_message(chat_id: Union[int, str], message_id: int, request: SendMessageRequest):
    """Reply to a specific message."""
    try:
        if isinstance(chat_id, str) and not chat_id.lstrip('-').isdigit():
            entity = await client.get_entity(chat_id)
        else:
            entity = await client.get_entity(int(chat_id))
        
        result = await client.send_message(entity, request.message, reply_to=message_id)
        
        return {
            "success": True,
            "message_id": result.id,
            "date": result.date.isoformat() if result.date else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/chats/{chat_id}/messages/{message_id}")
async def edit_message(chat_id: Union[int, str], message_id: int, request: EditMessageRequest):
    """Edit a message."""
    try:
        if isinstance(chat_id, str) and not chat_id.lstrip('-').isdigit():
            entity = await client.get_entity(chat_id)
        else:
            entity = await client.get_entity(int(chat_id))
        
        result = await client.edit_message(entity, message_id, request.new_text)
        
        return {"success": True, "message_id": result.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/chats/{chat_id}/messages/{message_id}")
async def delete_message(chat_id: Union[int, str], message_id: int):
    """Delete a message."""
    try:
        if isinstance(chat_id, str) and not chat_id.lstrip('-').isdigit():
            entity = await client.get_entity(chat_id)
        else:
            entity = await client.get_entity(int(chat_id))
        
        await client.delete_messages(entity, [message_id])
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chats/{chat_id}/messages/{message_id}/forward")
async def forward_message(chat_id: Union[int, str], message_id: int, to_chat_id: Union[int, str] = Query(...)):
    """Forward a message to another chat."""
    try:
        if isinstance(chat_id, str) and not chat_id.lstrip('-').isdigit():
            from_entity = await client.get_entity(chat_id)
        else:
            from_entity = await client.get_entity(int(chat_id))
        
        if isinstance(to_chat_id, str) and not to_chat_id.lstrip('-').isdigit():
            to_entity = await client.get_entity(to_chat_id)
        else:
            to_entity = await client.get_entity(int(to_chat_id))
        
        result = await client.forward_messages(to_entity, message_id, from_entity)
        
        return {"success": True, "message_id": result.id if hasattr(result, 'id') else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chats/{chat_id}/read")
async def mark_as_read(chat_id: Union[int, str]):
    """Mark all messages in chat as read."""
    try:
        if isinstance(chat_id, str) and not chat_id.lstrip('-').isdigit():
            entity = await client.get_entity(chat_id)
        else:
            entity = await client.get_entity(int(chat_id))
        
        await client.send_read_acknowledge(entity)
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chats/{chat_id}/messages/{message_id}/pin")
async def pin_message(chat_id: Union[int, str], message_id: int):
    """Pin a message."""
    try:
        if isinstance(chat_id, str) and not chat_id.lstrip('-').isdigit():
            entity = await client.get_entity(chat_id)
        else:
            entity = await client.get_entity(int(chat_id))
        
        await client.pin_message(entity, message_id)
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chats/{chat_id}/search")
async def search_messages(chat_id: Union[int, str], query: str = Query(...), limit: int = Query(default=20, le=100)):
    """Search messages in a chat."""
    try:
        if isinstance(chat_id, str) and not chat_id.lstrip('-').isdigit():
            entity = await client.get_entity(chat_id)
        else:
            entity = await client.get_entity(int(chat_id))
        
        messages = await client.get_messages(entity, limit=limit, search=query)
        
        return {
            "messages": [format_message(msg) for msg in messages],
            "count": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}/status")
async def get_user_status(user_id: Union[int, str]):
    """Get user online status."""
    try:
        if isinstance(user_id, str) and not user_id.lstrip('-').isdigit():
            entity = await client.get_entity(user_id)
        else:
            entity = await client.get_entity(int(user_id))
        
        status = getattr(entity, "status", None)
        status_str = type(status).__name__ if status else "Unknown"
        
        # Parse status type
        if "Online" in status_str:
            result = "online"
        elif "Recently" in status_str:
            result = "recently"
        elif "LastWeek" in status_str:
            result = "last_week"
        elif "LastMonth" in status_str:
            result = "last_month"
        elif "Offline" in status_str:
            result = "offline"
        else:
            result = status_str.lower()
        
        return {"user_id": entity.id, "status": result, "raw_status": status_str}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}/photos")
async def get_user_photos(user_id: Union[int, str], limit: int = Query(default=10, le=50)):
    """Get user profile photos."""
    try:
        if isinstance(user_id, str) and not user_id.lstrip('-').isdigit():
            entity = await client.get_entity(user_id)
        else:
            entity = await client.get_entity(int(user_id))
        
        photos = await client.get_profile_photos(entity, limit=limit)
        
        return {
            "photos": [{"id": p.id, "date": p.date.isoformat() if p.date else None} for p in photos],
            "count": len(photos)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gifs/search")
async def search_gifs(query: str = Query(...), limit: int = Query(default=10, le=50)):
    """Search for GIFs."""
    try:
        from telethon.tl.types import InputBotInlineMessageID
        
        result = await client.inline_query("@gif", query)
        gifs = []
        
        for i, r in enumerate(result):
            if i >= limit:
                break
            gifs.append({
                "id": i,
                "title": getattr(r, "title", None),
                "description": getattr(r, "description", None),
            })
        
        return {"gifs": gifs, "count": len(gifs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)

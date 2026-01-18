"""
BinaApp Chat System - Real-time messaging for delivery orders
Supports WebSocket for instant messaging between customers, owners, and riders
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form, Depends
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime
import json
import uuid
import os
import logging
import cloudinary
import cloudinary.uploader

from app.core.security import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Configure Cloudinary
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET
    )


# =====================================================
# CONNECTION MANAGER FOR WEBSOCKETS
# =====================================================

class ConnectionManager:
    """Manages WebSocket connections for real-time chat"""

    def __init__(self):
        # {conversation_id: {user_key: WebSocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, conversation_id: str, user_key: str):
        """Accept WebSocket connection and add to active connections"""
        await websocket.accept()
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = {}
        self.active_connections[conversation_id][user_key] = websocket
        logger.info(f"[Chat] {user_key} connected to conversation {conversation_id}")

    def disconnect(self, conversation_id: str, user_key: str):
        """Remove WebSocket connection"""
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].pop(user_key, None)
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]
        logger.info(f"[Chat] {user_key} disconnected from conversation {conversation_id}")

    async def send_to_conversation(self, conversation_id: str, message: dict, exclude_user: str = None):
        """Broadcast message to all users in a conversation"""
        if conversation_id in self.active_connections:
            disconnected = []
            for user_key, websocket in self.active_connections[conversation_id].items():
                if user_key != exclude_user:
                    try:
                        await websocket.send_json(message)
                    except Exception as e:
                        logger.warning(f"[Chat] Failed to send to {user_key}: {e}")
                        disconnected.append(user_key)

            # Clean up disconnected users
            for user_key in disconnected:
                self.active_connections[conversation_id].pop(user_key, None)

    async def send_to_user(self, conversation_id: str, user_key: str, message: dict):
        """Send message to a specific user in a conversation"""
        if conversation_id in self.active_connections:
            websocket = self.active_connections[conversation_id].get(user_key)
            if websocket:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"[Chat] Failed to send to {user_key}: {e}")

    def get_online_users(self, conversation_id: str) -> List[str]:
        """Get list of online users in a conversation"""
        if conversation_id in self.active_connections:
            return list(self.active_connections[conversation_id].keys())
        return []


# Global connection manager instance
manager = ConnectionManager()


# =====================================================
# PYDANTIC MODELS
# =====================================================

class CreateConversationRequest(BaseModel):
    order_id: Optional[str] = None
    website_id: str
    customer_name: str
    customer_phone: str


class SendMessageRequest(BaseModel):
    conversation_id: str
    sender_type: str  # customer, owner, rider, system
    sender_id: str
    sender_name: str
    message_type: str = "text"  # text, image, location, payment, status, voice
    message_text: Optional[str] = None
    content: Optional[str] = None
    message: Optional[str] = None
    media_url: Optional[str] = None
    metadata: Optional[dict] = None


class MarkReadRequest(BaseModel):
    conversation_id: str
    user_type: str  # customer, owner, rider


class UpdateLocationRequest(BaseModel):
    rider_id: str
    order_id: str
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    heading: Optional[float] = None
    speed: Optional[float] = None


# =====================================================
# PHONE-BASED CHAT MODELS (Simplified)
# =====================================================

class ConversationCreate(BaseModel):
    website_id: str
    customer_name: str
    customer_phone: str


class MessageCreate(BaseModel):
    conversation_id: str
    sender_type: str  # 'customer' or 'restaurant'
    sender_name: str
    message_text: str


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def get_supabase():
    """Get Supabase client"""
    from supabase import create_client, Client

    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = (
        os.getenv("SUPABASE_SERVICE_KEY") or
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
        os.getenv("SUPABASE_KEY") or
        os.getenv("SUPABASE_ANON_KEY") or
        ""
    )

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _extract_missing_column(err: object) -> Optional[str]:
    """
    Best-effort parsing for PostgREST missing-column errors.
    Handles dict-like errors and stringified errors.
    """
    try:
        if isinstance(err, dict):
            msg = str(err.get("message") or err.get("details") or err)
        else:
            msg = str(err)
    except Exception:
        return None

    # Typical: column "is_read" of relation "chat_messages" does not exist
    needle = 'column "'
    if needle in msg and '" of relation' in msg and "does not exist" in msg:
        try:
            return msg.split(needle, 1)[1].split('"', 1)[0]
        except Exception:
            return None
    return None


def _insert_with_column_fallback(supabase, table: str, row: dict, max_retries: int = 6):
    """
    Insert with automatic removal of unknown columns.
    This makes chat endpoints compatible with multiple schema versions in the wild.
    """
    data = dict(row)
    for _ in range(max_retries):
        result = supabase.table(table).insert(data).execute()
        err = getattr(result, "error", None)
        if result.data:
            return result
        if not err:
            return result

        missing = _extract_missing_column(err)
        if missing and missing in data:
            logger.warning(f"[Chat] {table} insert: missing column '{missing}', retrying without it")
            data.pop(missing, None)
            continue

        # Some schemas use `content` instead of `message` (or vice versa)
        err_str = str(err)
        if 'column "message"' in err_str and "does not exist" in err_str and "message" in data:
            data.pop("message", None)
            continue
        if 'column "content"' in err_str and "does not exist" in err_str and "content" in data:
            data.pop("content", None)
            continue

        return result

    return supabase.table(table).insert(data).execute()


# =====================================================
# REST API ENDPOINTS
# =====================================================

@router.post("/conversations/create")
async def create_conversation(request: CreateConversationRequest):
    """Create a new chat conversation for an order"""
    import re

    try:
        supabase = get_supabase()

        # =====================================================
        # CRITICAL: VALIDATE WEBSITE ID (Single Source of Truth)
        # =====================================================
        # GUARD 1: Reject null/empty website IDs
        if not request.website_id or not request.website_id.strip():
            logger.warning(f"[Chat] REJECTED: Conversation creation with empty website_id")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "MISSING_WEBSITE_ID",
                    "message": "Website ID is required for conversation creation"
                }
            )

        # GUARD 2: Validate UUID format (fail fast on malformed IDs)
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        if not uuid_pattern.match(request.website_id.strip()):
            logger.warning(f"[Chat] REJECTED: Invalid UUID format for website_id: {request.website_id[:50]}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "INVALID_UUID_FORMAT",
                    "message": "Website ID must be a valid UUID"
                }
            )

        # GUARD 3: Verify website exists in database (AUTHORITATIVE CHECK)
        website_check = supabase.table("websites").select("id, business_name, name").eq(
            "id", request.website_id.strip()
        ).execute()

        if not website_check.data:
            logger.warning(f"[Chat] REJECTED: Website not found in database: {request.website_id}")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "WEBSITE_NOT_FOUND",
                    "message": "No website found with this ID. Cannot create conversation for non-existent website."
                }
            )

        # Use the CANONICAL ID from database (not user-provided)
        website_row = website_check.data[0]
        canonical_website_id = website_row["id"]
        website_name = website_row.get("business_name") or website_row.get("name") or ""
        logger.info(f"[Chat] Website validated: {canonical_website_id}")

        # =====================================================
        # GENERATE CONVERSATION ID (Server-side only, never client)
        # =====================================================
        conversation_id = str(uuid.uuid4())
        logger.info(f"[Chat] Generated server-side conversation_id: {conversation_id}")

        customer_user_id = f"customer_{request.customer_phone}"

        # Create conversation with VALIDATED website_id
        conv_data = {
            "id": conversation_id,
            "order_id": request.order_id,
            "website_id": canonical_website_id,  # Use canonical DB ID
            "website_name": website_name,
            # Some schema versions require customer_id NOT NULL
            "customer_id": customer_user_id,
            "customer_name": request.customer_name,
            "customer_phone": request.customer_phone,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        result = _insert_with_column_fallback(supabase, "chat_conversations", conv_data)

        if not result.data and getattr(result, "error", None):
            logger.error(f"[Chat] Conversation insert error: {result.error}")
            raise HTTPException(status_code=500, detail="Failed to create conversation")

        # Optional: chat_participants may not exist in older deployments
        try:
            supabase.table("chat_participants").insert({
                "conversation_id": conversation_id,
                # Support both schema styles: participant_type vs user_type
                "participant_type": "customer",
                "user_type": "customer",
                "participant_name": request.customer_name,
                "user_name": request.customer_name,
                "participant_phone": request.customer_phone
            }).execute()

            supabase.table("chat_participants").insert({
                "conversation_id": conversation_id,
                "participant_type": "owner",
                "user_type": "owner",
                "participant_name": "Pemilik Kedai",
                "user_name": "Pemilik Kedai",
                "participant_phone": None
            }).execute()
        except Exception as part_err:
            logger.warning(f"[Chat] chat_participants insert skipped/failed: {part_err}")

        # Add system welcome message (schema-compatible)
        welcome_text = "Perbualan dimulakan. Pemilik kedai akan membalas sebentar lagi."
        _insert_with_column_fallback(
            supabase,
            "chat_messages",
            {
                "id": str(uuid.uuid4()),
                "conversation_id": conversation_id,
                "sender_type": "system",
                "message": welcome_text,
                "content": welcome_text,
                "message_text": welcome_text,
                "is_read": False,
                "created_at": datetime.utcnow().isoformat()
            }
        )

        logger.info(f"[Chat] Created conversation {conversation_id} for website {request.website_id}")

        return {
            "conversation_id": conversation_id,
            "customer_id": customer_user_id,
            "status": "created"
        }

    except Exception as e:
        logger.error(f"[Chat] Failed to create conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation details and messages"""
    try:
        supabase = get_supabase()

        # Get conversation
        conv = supabase.table("chat_conversations").select("*").eq("id", conversation_id).single().execute()

        if not conv.data:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Get messages
        messages = supabase.table("chat_messages").select(
            "id, conversation_id, message_text, sender_type, sender_name, message_type, media_url, metadata, is_read, created_at"
        ).eq(
            "conversation_id", conversation_id
        ).order("created_at").execute()

        messages_data = messages.data or []
        # Backwards compatibility for clients expecting "content"
        for msg in messages_data:
            if not msg.get("message_text"):
                msg["message_text"] = msg.get("message") or msg.get("content") or ""
            if not msg.get("content"):
                msg["content"] = msg.get("message_text") or msg.get("message") or ""

        # Get participants
        participants_data = []
        try:
            participants = supabase.table("chat_participants").select("*").eq(
                "conversation_id", conversation_id
            ).execute()
            participants_data = participants.data or []
        except Exception as part_err:
            # Older deployments may not have chat_participants table
            logger.warning(f"[Chat] Participants unavailable (table missing?): {part_err}")

        return {
            "conversation": conv.data,
            "messages": messages_data,
            "participants": participants_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Chat] Failed to get conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations")
async def get_conversations(
    website_ids: str = None,
    status: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Get conversations filtered by website_ids (comma-separated) or all if none provided"""
    try:
        supabase = get_supabase()

        # SECURITY: Extract user_id from authenticated token
        user_id = current_user.get("sub") or current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")

        # SECURITY: Get only websites owned by this user
        user_websites = supabase.table("websites").select("id").eq("user_id", user_id).execute()
        if not user_websites.data:
            return {"conversations": []}

        owned_website_ids = [str(w["id"]) for w in user_websites.data]

        # Get conversations without nested query to avoid JOIN issues
        query = supabase.table("chat_conversations").select("*")

        # Filter by multiple website_ids if provided, but ONLY if user owns them
        if website_ids:
            ids_list = [id.strip() for id in website_ids.split(',') if id.strip()]
            # SECURITY: Filter to only websites owned by user
            allowed_ids = [wid for wid in ids_list if wid in owned_website_ids]
            if allowed_ids:
                query = query.in_("website_id", allowed_ids)
                logger.info(f"[Chat] Filtering conversations by website_ids: {allowed_ids}")
            else:
                # User tried to access websites they don't own
                logger.warning(f"[Chat] User {user_id} attempted to access unauthorized websites: {ids_list}")
                return {"conversations": []}
        else:
            # SECURITY: If no filter specified, only show user's websites
            query = query.in_("website_id", owned_website_ids)

        if status:
            query = query.eq("status", status)

        result = query.order("updated_at", desc=True).execute()
        conversations = result.data or []

        # Fetch last message for each conversation separately
        for conv in conversations:
            try:
                # Use canonical message_text for previews
                messages = supabase.table("chat_messages").select(
                    "id, message_text, sender_type, sender_name, message_type, media_url, is_read, created_at"
                ).eq("conversation_id", conv["id"]).order(
                    "created_at", desc=True
                ).limit(10).execute()

                # Reverse to get chronological order
                conv["chat_messages"] = list(reversed(messages.data or []))
            except Exception as msg_err:
                logger.warning(f"[Chat] Failed to fetch messages for conversation {conv['id']}: {msg_err}")
                conv["chat_messages"] = []

        logger.info(f"[Chat] Retrieved {len(conversations)} conversations")
        return {"conversations": conversations}

    except Exception as e:
        logger.error(f"[Chat] Failed to get conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load conversations: {str(e)}")


@router.get("/conversations/website/{website_id}")
async def get_website_conversations(
    website_id: str,
    status: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all conversations for a single website (owner dashboard) - DEPRECATED: Use /conversations?website_ids=ID instead"""
    try:
        supabase = get_supabase()

        # SECURITY: Extract user_id from authenticated token
        user_id = current_user.get("sub") or current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")

        # SECURITY: Verify user owns this website
        website_check = supabase.table("websites").select("id").eq("id", website_id).eq("user_id", user_id).execute()
        if not website_check.data:
            logger.warning(f"[Chat] User {user_id} attempted to access unauthorized website: {website_id}")
            raise HTTPException(
                status_code=403,
                detail="Access denied: You don't own this website"
            )

        # Get conversations without nested query to avoid JOIN issues
        query = supabase.table("chat_conversations").select("*").eq("website_id", website_id)

        if status:
            query = query.eq("status", status)

        result = query.order("updated_at", desc=True).execute()
        conversations = result.data or []

        # Fetch last message for each conversation separately
        for conv in conversations:
            try:
                # Use canonical message_text for previews
                messages = supabase.table("chat_messages").select(
                    "id, message_text, sender_type, sender_name, message_type, media_url, is_read, created_at"
                ).eq("conversation_id", conv["id"]).order(
                    "created_at", desc=True
                ).limit(10).execute()

                # Reverse to get chronological order
                conv["chat_messages"] = list(reversed(messages.data or []))
            except Exception as msg_err:
                logger.warning(f"[Chat] Failed to fetch messages for conversation {conv['id']}: {msg_err}")
                conv["chat_messages"] = []

        logger.info(f"[Chat] Retrieved {len(conversations)} conversations for website {website_id}")
        return {"conversations": conversations}

    except Exception as e:
        logger.error(f"[Chat] Failed to get website conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load conversations: {str(e)}")


@router.get("/conversations/order/{order_id}")
async def get_conversation_by_order(order_id: str):
    """Get or create conversation for an order"""
    try:
        supabase = get_supabase()

        # Check if conversation exists
        result = supabase.table("chat_conversations").select("*").eq("order_id", order_id).execute()

        if result.data:
            conversation = result.data[0]
            # Backfill customer_id for legacy rows (customer_id not stored in DB)
            if not conversation.get("customer_id") and conversation.get("customer_phone"):
                conversation["customer_id"] = f"customer_{conversation['customer_phone']}"
            return {"conversation": conversation, "exists": True}

        return {"conversation": None, "exists": False}

    except Exception as e:
        logger.error(f"[Chat] Failed to get conversation by order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages/send")
async def send_message(request: SendMessageRequest):
    """Send a message via REST API"""
    try:
        supabase = get_supabase()

        message_id = str(uuid.uuid4())

        # Map request.message_text/message/content to canonical message_text
        message_text = (request.message_text or request.message or request.content or "").strip()

        # Validate message is not empty
        if not message_text:
            message_text = "Mesej kosong"  # Fallback to prevent NULL constraint violation

        # Save message with schema compatibility (older deployments may not have is_read/content/etc)
        insert_row = {
            "id": message_id,
            "conversation_id": request.conversation_id,
            "sender_type": request.sender_type,
            "sender_id": request.sender_id,
            "sender_name": request.sender_name,
            "message_type": request.message_type,
            "message_text": message_text,
            "content": message_text,
            "message": message_text,
            "media_url": request.media_url,
            "metadata": request.metadata,
            "is_read": False,
            "created_at": datetime.utcnow().isoformat()
        }
        insert_result = _insert_with_column_fallback(supabase, "chat_messages", insert_row)
        if not insert_result.data and getattr(insert_result, "error", None):
            logger.error(f"[Chat] Message insert error: {insert_result.error}")
            raise HTTPException(status_code=500, detail="Failed to send message")

        # Best-effort: bump conversation updated_at (some schemas have trigger; some don't)
        try:
            supabase.table("chat_conversations").update({
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", request.conversation_id).execute()
        except Exception:
            pass

        # WebSocket broadcast payload (UI-compatible; does not depend on DB schema)
        message_data = {
            "id": message_id,
            "conversation_id": request.conversation_id,
            "sender_type": request.sender_type,
            "sender_id": request.sender_id,
            "sender_name": request.sender_name,
            "message_type": request.message_type,
            "message_text": message_text,
            "content": message_text,
            "message": message_text,
            "media_url": request.media_url,
            "metadata": request.metadata,
            "is_read": False,
            "created_at": datetime.utcnow().isoformat()
        }

        # Broadcast to WebSocket clients
        await manager.send_to_conversation(
            request.conversation_id,
            {
                "type": "new_message",
                "message": message_data
            }
        )

        logger.info(f"[Chat] Message sent in conversation {request.conversation_id} by {request.sender_type}")

        return {"message_id": message_id, "status": "sent"}

    except Exception as e:
        logger.error(f"[Chat] Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages/upload-image")
async def upload_chat_image(
    conversation_id: str = Form(...),
    sender_type: str = Form(...),
    sender_id: str = Form(...),
    sender_name: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload image and send as message"""
    try:
        if not CLOUDINARY_CLOUD_NAME:
            raise HTTPException(status_code=500, detail="Cloudinary not configured")

        # Upload to Cloudinary
        contents = await file.read()
        result = cloudinary.uploader.upload(
            contents,
            folder="binaapp/chat",
            resource_type="auto"
        )

        image_url = result.get("secure_url")

        # Send as message
        message_request = SendMessageRequest(
            conversation_id=conversation_id,
            sender_type=sender_type,
            sender_id=sender_id,
            sender_name=sender_name,
            message_type="image",
            content="Gambar",
            media_url=image_url
        )

        return await send_message(message_request)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Chat] Failed to upload image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages/upload-payment")
async def upload_payment_proof(
    conversation_id: str = Form(...),
    sender_id: str = Form(...),
    sender_name: str = Form(...),
    order_id: str = Form(...),
    amount: float = Form(0),
    file: UploadFile = File(...)
):
    """Upload payment proof"""
    try:
        if not CLOUDINARY_CLOUD_NAME:
            raise HTTPException(status_code=500, detail="Cloudinary not configured")

        # Upload to Cloudinary
        contents = await file.read()
        result = cloudinary.uploader.upload(
            contents,
            folder="binaapp/payments",
            resource_type="auto"
        )

        image_url = result.get("secure_url")

        # Send as payment message
        message_request = SendMessageRequest(
            conversation_id=conversation_id,
            sender_type="customer",
            sender_id=sender_id,
            sender_name=sender_name,
            message_type="payment",
            content="Bukti Pembayaran",
            media_url=image_url,
            metadata={
                "order_id": order_id,
                "amount": amount,
                "status": "pending_verification"
            }
        )

        return await send_message(message_request)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Chat] Failed to upload payment proof: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages/mark-read")
async def mark_messages_read(request: MarkReadRequest):
    """Mark all messages in conversation as read for a user type"""
    try:
        supabase = get_supabase()

        # Update messages not sent by this user type (schema-compatible: is_read/read_at may not exist)
        try:
            update_result = supabase.table("chat_messages").update({
                "is_read": True,
                "read_at": datetime.utcnow().isoformat()
            }).eq("conversation_id", request.conversation_id).neq(
                "sender_type", request.user_type
            ).execute()
            if getattr(update_result, "error", None):
                missing = _extract_missing_column(update_result.error)
                if missing in {"is_read", "read_at"}:
                    logger.warning(f"[Chat] mark-read skipped: {update_result.error}")
        except Exception as upd_err:
            logger.warning(f"[Chat] mark-read skipped/failed: {upd_err}")

        # Reset unread count for this user type
        update_data = {}
        if request.user_type == "customer":
            update_data["unread_customer"] = 0
        elif request.user_type == "owner":
            update_data["unread_owner"] = 0
        elif request.user_type == "rider":
            update_data["unread_rider"] = 0

        if update_data:
            # Columns may not exist in older schema; ignore if so
            try:
                result = supabase.table("chat_conversations").update(update_data).eq(
                    "id", request.conversation_id
                ).execute()
                if getattr(result, "error", None):
                    missing = _extract_missing_column(result.error)
                    if missing and missing in update_data:
                        logger.warning(f"[Chat] unread reset skipped: {result.error}")
            except Exception as conv_upd_err:
                logger.warning(f"[Chat] unread reset skipped/failed: {conv_upd_err}")

        # Notify other users
        await manager.send_to_conversation(
            request.conversation_id,
            {
                "type": "messages_read",
                "user_type": request.user_type
            }
        )

        return {"status": "marked_read"}

    except Exception as e:
        logger.error(f"[Chat] Failed to mark messages read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rider/update-location")
async def update_rider_location(request: UpdateLocationRequest):
    """Update rider's live location"""
    try:
        supabase = get_supabase()

        # Save to rider_locations table
        supabase.table("rider_locations").insert({
            "rider_id": request.rider_id,
            "order_id": request.order_id,
            "latitude": request.latitude,
            "longitude": request.longitude
        }).execute()

        # Also update rider's current location
        supabase.table("riders").update({
            "current_latitude": request.latitude,
            "current_longitude": request.longitude,
            "last_location_update": datetime.utcnow().isoformat()
        }).eq("id", request.rider_id).execute()

        # Find conversation for this order and broadcast location
        conv = supabase.table("chat_conversations").select("id").eq("order_id", request.order_id).execute()

        if conv.data:
            for c in conv.data:
                await manager.send_to_conversation(
                    c["id"],
                    {
                        "type": "rider_location",
                        "data": {
                            "rider_id": request.rider_id,
                            "latitude": request.latitude,
                            "longitude": request.longitude,
                            "heading": request.heading,
                            "speed": request.speed,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                )

        return {"status": "updated"}

    except Exception as e:
        logger.error(f"[Chat] Failed to update rider location: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rider/location/{order_id}")
async def get_rider_location(order_id: str):
    """Get latest rider location for an order"""
    try:
        supabase = get_supabase()

        result = supabase.table("rider_locations").select("*").eq(
            "order_id", order_id
        ).order("recorded_at", desc=True).limit(1).execute()

        if result.data:
            return {"location": result.data[0]}
        return {"location": None}

    except Exception as e:
        logger.error(f"[Chat] Failed to get rider location: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/{conversation_id}/close")
async def close_conversation(conversation_id: str):
    """Close a conversation"""
    try:
        supabase = get_supabase()

        supabase.table("chat_conversations").update({
            "status": "closed"
        }).eq("id", conversation_id).execute()

        # Send system message
        system_text = "Perbualan telah ditutup."
        _insert_with_column_fallback(
            supabase,
            "chat_messages",
            {
                "conversation_id": conversation_id,
                "sender_type": "system",
                "message_text": system_text,
                "content": system_text,
                "message": system_text,
                "is_read": False,
                "created_at": datetime.utcnow().isoformat()
            }
        )

        # Notify via WebSocket
        await manager.send_to_conversation(
            conversation_id,
            {
                "type": "conversation_closed",
                "conversation_id": conversation_id
            }
        )

        return {"status": "closed"}

    except Exception as e:
        logger.error(f"[Chat] Failed to close conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/{conversation_id}/add-rider")
async def add_rider_to_conversation(conversation_id: str, rider_id: str, rider_name: str):
    """Add rider to conversation when assigned to order"""
    try:
        supabase = get_supabase()

        # Add rider as participant - use ONLY existing columns
        # Schema: id, conversation_id, participant_type, participant_name, participant_phone, joined_at, created_at
        # Note: Using insert instead of upsert since we don't have unique constraint on (conversation_id, participant_type)
        supabase.table("chat_participants").insert({
            "conversation_id": conversation_id,
            "participant_type": "rider",
            "participant_name": rider_name,
            "participant_phone": None  # Rider phone could be added later if needed
        }).execute()

        # Send system message
        system_text = f"Rider {rider_name} telah ditugaskan untuk penghantaran ini."
        _insert_with_column_fallback(
            supabase,
            "chat_messages",
            {
                "conversation_id": conversation_id,
                "sender_type": "system",
                "message_text": system_text,
                "content": system_text,
                "message": system_text,
                "is_read": False,
                "created_at": datetime.utcnow().isoformat()
            }
        )

        # Notify via WebSocket
        await manager.send_to_conversation(
            conversation_id,
            {
                "type": "rider_assigned",
                "rider_id": rider_id,
                "rider_name": rider_name
            }
        )

        return {"status": "rider_added"}

    except Exception as e:
        logger.error(f"[Chat] Failed to add rider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# SIMPLIFIED PHONE-BASED CHAT ENDPOINTS
# =====================================================

@router.post("/chat/conversations")
async def create_or_get_phone_conversation(data: ConversationCreate):
    """
    Create or get existing conversation for phone number
    Simple phone-based chat system - no user accounts needed
    """
    try:
        supabase = get_supabase()

        # Validate inputs
        if not data.website_id or not data.customer_phone:
            raise HTTPException(
                status_code=400,
                detail="website_id and customer_phone are required"
            )

        # Check if conversation exists for this phone + website
        existing = supabase.table('chat_conversations')\
            .select('*')\
            .eq('website_id', data.website_id)\
            .eq('customer_phone', data.customer_phone)\
            .eq('status', 'active')\
            .execute()

        if existing.data and len(existing.data) > 0:
            logger.info(f"[Chat] Found existing conversation for phone {data.customer_phone}")
            return existing.data[0]

        # Create new conversation
        conversation_id = str(uuid.uuid4())
        customer_id = f"customer_{data.customer_phone}"

        conv_data = {
            'id': conversation_id,
            'website_id': data.website_id,
            'customer_name': data.customer_name,
            'customer_phone': data.customer_phone,
            'customer_id': customer_id,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat()
        }

        result = supabase.table('chat_conversations').insert(conv_data).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create conversation")

        logger.info(f"[Chat] Created new conversation {conversation_id} for phone {data.customer_phone}")
        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Chat] Error creating/getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/messages")
async def send_chat_message(message: MessageCreate):
    """
    Send chat message in phone-based conversation
    """
    try:
        supabase = get_supabase()

        # Validate message text
        text = message.message_text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="message_text cannot be empty")

        message_id = str(uuid.uuid4())

        # Prepare message data - use message_text and content for compatibility
        message_data = {
            'id': message_id,
            'conversation_id': message.conversation_id,
            'sender_type': message.sender_type,
            'sender_name': message.sender_name,
            'message_text': text,
            'content': text,
            'message': text,
            'is_read': False,
            'created_at': datetime.utcnow().isoformat()
        }

        result = _insert_with_column_fallback(supabase, 'chat_messages', message_data)

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to send message")

        # Prepare response with content field for BinaChat compatibility
        response_data = result.data[0]
        if not response_data.get('content'):
            response_data['content'] = response_data.get('message') or response_data.get('message_text') or ''

        # Broadcast to WebSocket clients if they're connected
        await manager.send_to_conversation(
            message.conversation_id,
            {
                "type": "new_message",
                "message": response_data
            }
        )

        logger.info(f"[Chat] Message sent in conversation {message.conversation_id}")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Chat] Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/conversations/{conversation_id}/messages")
async def get_chat_messages(conversation_id: str):
    """
    Get all messages for a conversation
    """
    try:
        supabase = get_supabase()

        result = supabase.table('chat_messages')\
            .select('id, conversation_id, message_text, sender_type, sender_name, message_type, media_url, metadata, is_read, created_at')\
            .eq('conversation_id', conversation_id)\
            .order('created_at', desc=False)\
            .execute()

        messages = result.data or []

        # Ensure message_text and content are populated for compatibility
        for msg in messages:
            if not msg.get('message_text'):
                msg['message_text'] = msg.get('message') or msg.get('content') or ''
            if not msg.get('content'):
                msg['content'] = msg.get('message_text') or msg.get('message') or ''

        logger.info(f"[Chat] Retrieved {len(messages)} messages for conversation {conversation_id}")
        return messages

    except Exception as e:
        logger.error(f"[Chat] Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# WEBSOCKET ENDPOINT
# =====================================================

@router.websocket("/ws/{conversation_id}/{user_type}/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: str,
    user_type: str,
    user_id: str
):
    """WebSocket connection for real-time chat"""
    user_key = f"{user_type}_{user_id}"
    await manager.connect(websocket, conversation_id, user_key)

    # Note: chat_participants table only has: id, conversation_id, participant_type,
    # participant_name, participant_phone, joined_at, created_at
    # is_online and last_seen columns don't exist, so we skip updating them
    logger.info(f"[Chat] User {user_type}:{user_id} connected to conversation {conversation_id}")

    # Notify others that user joined
    await manager.send_to_conversation(
        conversation_id,
        {
            "type": "user_joined",
            "user_type": user_type,
            "user_id": user_id,
            "online_users": manager.get_online_users(conversation_id)
        },
        exclude_user=user_key
    )

    try:
        while True:
            data = await websocket.receive_json()

            # Handle different message types
            if data.get("type") == "message":
                # Send message via REST handler
                await send_message(SendMessageRequest(
                    conversation_id=conversation_id,
                    sender_type=user_type,
                    sender_id=user_id,
                    sender_name=data.get("sender_name", ""),
                    message_type=data.get("message_type", "text"),
                    message_text=data.get("message_text") or data.get("content") or data.get("message", ""),
                    media_url=data.get("media_url"),
                    metadata=data.get("metadata")
                ))

            elif data.get("type") == "typing":
                # Broadcast typing indicator
                await manager.send_to_conversation(
                    conversation_id,
                    {
                        "type": "typing",
                        "user_type": user_type,
                        "user_id": user_id,
                        "is_typing": data.get("is_typing", False)
                    },
                    exclude_user=user_key
                )

            elif data.get("type") == "read":
                # Mark messages as read
                await mark_messages_read(MarkReadRequest(
                    conversation_id=conversation_id,
                    user_type=user_type
                ))

            elif data.get("type") == "location":
                # Rider sharing location
                if user_type == "rider":
                    location_data = data.get("location", {})
                    await manager.send_to_conversation(
                        conversation_id,
                        {
                            "type": "rider_location",
                            "data": {
                                "rider_id": user_id,
                                **location_data,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        }
                    )

            elif data.get("type") == "ping":
                # Respond to ping (keep-alive)
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(conversation_id, user_key)

        # Note: chat_participants table doesn't have is_online/last_seen columns
        # Skipping database update for offline status
        logger.info(f"[Chat] User {user_type}:{user_id} disconnected from conversation {conversation_id}")

        # Notify others that user left
        await manager.send_to_conversation(
            conversation_id,
            {
                "type": "user_left",
                "user_type": user_type,
                "user_id": user_id,
                "online_users": manager.get_online_users(conversation_id)
            }
        )

    except Exception as e:
        logger.error(f"[Chat] WebSocket error: {e}")
        manager.disconnect(conversation_id, user_key)

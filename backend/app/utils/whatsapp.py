"""
WhatsApp Business API Integration for BinaApp Delivery System

This module handles sending WhatsApp notifications to:
- Owners when new orders are placed
- Riders when orders are assigned to them
- Customers when order status changes

Currently in SIMULATION MODE - logs messages to console instead of sending
To enable real WhatsApp sending:
1. Get WhatsApp Business API credentials from Meta
2. Set WHATSAPP_API_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env
3. Uncomment the API call code below
"""

import os
import requests
from typing import Optional, List, Dict
from loguru import logger

WHATSAPP_API_URL = "https://graph.facebook.com/v18.0"
WHATSAPP_TOKEN = os.getenv("WHATSAPP_API_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")


def send_whatsapp_message(
    to_phone: str,
    message: str,
    template_name: Optional[str] = None
) -> bool:
    """
    Send WhatsApp message via Meta Business API

    Args:
        to_phone: Recipient phone number (Malaysia format: 0123456789)
        message: Message text to send
        template_name: Optional WhatsApp template name (for approved templates)

    Returns:
        bool: True if message sent successfully (or would be sent in production)
    """

    # Format phone number (remove leading 0, add 60 for Malaysia)
    formatted_phone = to_phone.replace(" ", "").replace("-", "")
    if formatted_phone.startswith("0"):
        formatted_phone = "60" + formatted_phone[1:]

    # Log the message that would be sent
    logger.info(f"[WhatsApp] Would send to {formatted_phone}:")
    logger.info(f"[WhatsApp] Message: {message[:100]}...")  # Log first 100 chars

    # TODO: Uncomment when WhatsApp Business API is set up
    # if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
    #     logger.warning("[WhatsApp] API credentials not configured")
    #     return False

    # try:
    #     response = requests.post(
    #         f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_ID}/messages",
    #         headers={
    #             "Authorization": f"Bearer {WHATSAPP_TOKEN}",
    #             "Content-Type": "application/json"
    #         },
    #         json={
    #             "messaging_product": "whatsapp",
    #             "to": formatted_phone,
    #             "type": "text",
    #             "text": {"body": message}
    #         }
    #     )
    #
    #     if response.status_code == 200:
    #         logger.info(f"[WhatsApp] Message sent successfully to {formatted_phone}")
    #         return True
    #     else:
    #         logger.error(f"[WhatsApp] Failed to send: {response.status_code} - {response.text}")
    #         return False
    # except Exception as e:
    #     logger.error(f"[WhatsApp] Error sending message: {e}")
    #     return False

    # For now, return True (simulation mode)
    return True


def notify_owner_new_order(
    owner_phone: str,
    order_number: str,
    customer_name: str,
    customer_phone: str,
    total_amount: float,
    items: List[Dict],
    delivery_address: str
) -> bool:
    """
    Notify restaurant owner about new order

    Args:
        owner_phone: Owner's phone number
        order_number: Order reference number
        customer_name: Customer's name
        customer_phone: Customer's phone
        total_amount: Total order amount
        items: List of order items with name, quantity, price
        delivery_address: Delivery address

    Returns:
        bool: True if notification sent successfully
    """

    # Format order items
    items_text = "\n".join([
        f"• {item.get('item_name', item.get('name', 'Item'))} x{item.get('quantity', 1)} - RM{(item.get('unit_price', item.get('price', 0)) * item.get('quantity', 1)):.2f}"
        for item in items[:10]  # Limit to 10 items to avoid too long message
    ])

    if len(items) > 10:
        items_text += f"\n... dan {len(items) - 10} item lagi"

    message = f"""🆕 *PESANAN BARU - {order_number}*

📋 *PESANAN DELIVERY*
{items_text}

👤 *Pelanggan:*
{customer_name}
📱 {customer_phone}
📍 {delivery_address}

💰 *TOTAL: RM{total_amount:.2f}*

📱 Urus pesanan di BinaApp Dashboard:
https://binaapp.my/profile

Terima kasih! 🙏"""

    return send_whatsapp_message(owner_phone, message)


def notify_rider_assigned(
    rider_phone: str,
    rider_name: str,
    order_number: str,
    customer_name: str,
    customer_phone: str,
    delivery_address: str,
    total_amount: float,
    pickup_address: Optional[str] = None
) -> bool:
    """
    Notify rider about order assignment

    Args:
        rider_phone: Rider's phone number
        rider_name: Rider's name
        order_number: Order reference number
        customer_name: Customer's name
        customer_phone: Customer's phone
        delivery_address: Delivery address
        total_amount: Total order amount
        pickup_address: Restaurant/pickup address (optional)

    Returns:
        bool: True if notification sent successfully
    """

    pickup_text = f"\n📍 Pickup: {pickup_address}" if pickup_address else ""

    message = f"""🆕 *ORDER ASSIGNED TO YOU*

Hi {rider_name}, ada order baru untuk anda!

📦 *Order: #{order_number}*
💰 Total: RM{total_amount:.2f}
{pickup_text}

👤 *Customer:*
{customer_name}
📱 {customer_phone}
📍 {delivery_address}

🛵 Buka rider app untuk mula penghantaran:
https://binaapp.my/rider

Selamat menghantar! 🚀"""

    return send_whatsapp_message(rider_phone, message)


def notify_customer_status_update(
    customer_phone: str,
    order_number: str,
    status: str,
    rider_name: Optional[str] = None,
    rider_phone: Optional[str] = None,
    eta_minutes: Optional[int] = None
) -> bool:
    """
    Notify customer about order status update

    Args:
        customer_phone: Customer's phone number
        order_number: Order reference number
        status: New order status
        rider_name: Rider's name (if assigned)
        rider_phone: Rider's phone (if assigned)
        eta_minutes: Estimated time of arrival in minutes (optional)

    Returns:
        bool: True if notification sent successfully
    """

    status_messages = {
        "confirmed": f"✅ Pesanan #{order_number} telah disahkan!\n\n📝 Restoran sedang menyediakan makanan anda.",
        "ready": f"🍽️ Makanan anda sudah siap!\n\n🛵 Menunggu rider untuk ambil pesanan.",
        "picked_up": f"📦 Rider telah ambil pesanan!\n\n🛵 {rider_name or 'Rider'} sedang dalam perjalanan ke lokasi anda.",
        "delivering": f"🚚 Pesanan dalam perjalanan!\n\n⏱️ Anggaran tiba: {eta_minutes or 15} minit\n🛵 Rider: {rider_name or 'Rider'}",
        "delivered": f"✅ Pesanan telah dihantar!\n\n🎉 Selamat menikmati hidangan anda!\nTerima kasih kerana memesan! 🙏",
        "cancelled": f"❌ Pesanan #{order_number} telah dibatalkan.\n\nJika ada pertanyaan, sila hubungi kami."
    }

    status_text = status_messages.get(status, f"Status pesanan #{order_number} dikemaskini")

    # Add rider contact info if available
    rider_info = ""
    if rider_name and rider_phone and status in ["picked_up", "delivering"]:
        rider_info = f"\n\n📞 Hubungi rider:\n{rider_name}\n📱 {rider_phone}"

    message = f"""📦 *UPDATE PESANAN #{order_number}*

{status_text}
{rider_info}

📱 Jejak pesanan anda:
https://binaapp.my/track/{order_number}"""

    return send_whatsapp_message(customer_phone, message)


def notify_rider_new_orders_available(
    rider_phone: str,
    rider_name: str,
    num_orders: int
) -> bool:
    """
    Notify rider about available orders waiting for pickup

    Args:
        rider_phone: Rider's phone number
        rider_name: Rider's name
        num_orders: Number of orders available

    Returns:
        bool: True if notification sent successfully
    """

    message = f"""🔔 *ORDERS AVAILABLE*

Hi {rider_name},

Ada {num_orders} order menunggu untuk diambil!

🛵 Log masuk ke rider app untuk lihat:
https://binaapp.my/rider

Jangan lepaskan peluang! 💰"""

    return send_whatsapp_message(rider_phone, message)

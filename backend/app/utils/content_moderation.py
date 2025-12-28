"""
Content Moderation Utility
Blocks illegal and harmful website content to protect platform owner
"""

import re
from typing import Tuple
from loguru import logger
import datetime

# ==================== ILLEGAL CONTENT KEYWORDS ====================

ILLEGAL_CONTENT_KEYWORDS = [
    # Scam/Fraud
    "scam", "phishing", "hack", "hacker", "carding", "credit card hack",
    "money transfer", "wire fraud", "get rich quick", "pyramid scheme",
    "skim cepat kaya", "penipuan", "tipu", "skim piramid",

    # Drugs
    "cocaine", "heroin", "meth", "ganja", "weed", "marijuana", "cannabis",
    "ketamine", "ecstasy", "mdma", "lsd", "drug dealer", "dadah", "pil kuda",
    "syabu", "ice drug",

    # Weapons
    "gun", "pistol", "rifle", "weapon", "ammo", "ammunition", "explosive",
    "bomb", "grenade", "senjata api", "pistol", "senapang",

    # Gambling (illegal in Malaysia)
    "casino", "gambling", "slot machine", "sports betting", "poker online",
    "judi", "kasino", "pertaruhan", "slot online", "togel", "4d", "toto haram",

    # Adult/Porn
    "porn", "xxx", "adult content", "escort", "prostitute", "sex service",
    "nude", "naked", "onlyfans clone", "webcam girl", "pelacur", "sundal",
    "urut batin", "happy ending", "gfe service",

    # Fake/Impersonation
    "fake ic", "fake passport", "fake license", "fake degree", "fake cert",
    "ic palsu", "lesen palsu", "sijil palsu", "diploma palsu",
    "clone website", "fake bank", "fake maybank", "fake cimb",

    # Counterfeit
    "replica", "counterfeit", "fake rolex", "fake gucci", "fake iphone",
    "first copy", "aaa quality", "tiruan", "barang tiruan",

    # Money laundering
    "money laundering", "offshore account", "tax evasion", "black money",
    "shell company", "cuci duit", "duit haram",

    # Illegal services
    "hacker for hire", "ddos service", "fake followers", "buy followers",
    "spam service", "email bombing",

    # Violence/Terrorism
    "terrorist", "isis", "jihad attack", "bomb making", "how to kill",
    "assassination", "keganasan", "pengganas",
]

# ==================== SUSPICIOUS PATTERNS ====================

SUSPICIOUS_PATTERNS = [
    # Too good to be true
    r"100%\s*guaranteed",
    r"guaranteed\s*profit",
    r"double\s*your\s*money",
    r"investment\s*return\s*\d{2,}%",
    r"keuntungan\s*dijamin",
    r"pulangan\s*\d{2,}%",

    # Urgency tactics (common in scams)
    r"act\s*now\s*or\s*lose",
    r"limited\s*slots?\s*only",
    r"today\s*only",
]


def is_content_allowed(description: str) -> Tuple[bool, str]:
    """
    Check if website content is legal and allowed

    Args:
        description: User's business description

    Returns:
        Tuple of (is_allowed, message)
        - is_allowed: True if content is safe, False if blocked
        - message: Reason for blocking or "OK" if allowed
    """
    if not description or not description.strip():
        return True, "OK"

    desc_lower = description.lower().strip()

    # Check for illegal keywords
    for keyword in ILLEGAL_CONTENT_KEYWORDS:
        if keyword in desc_lower:
            logger.warning(f"🚫 BLOCKED: Illegal content detected - '{keyword}'")
            logger.warning(f"   Description preview: {description[:100]}...")
            return False, "Kandungan tidak dibenarkan / Content not allowed"

    # Check suspicious patterns
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, desc_lower, re.IGNORECASE):
            logger.warning(f"🚫 BLOCKED: Suspicious pattern detected - '{pattern}'")
            logger.warning(f"   Description preview: {description[:100]}...")
            return False, "Kandungan mencurigakan / Suspicious content"

    return True, "OK"


def log_blocked_attempt(
    description: str,
    reason: str,
    ip_address: str = None,
    user_id: str = None
):
    """
    Log blocked content attempts for security review

    Args:
        description: The blocked business description
        reason: Reason for blocking
        ip_address: Optional IP address of requester
        user_id: Optional user ID
    """
    timestamp = datetime.datetime.now().isoformat()

    logger.warning("=" * 80)
    logger.warning("🚫 BLOCKED ATTEMPT - CONTENT MODERATION")
    logger.warning(f"Time: {timestamp}")
    logger.warning(f"Reason: {reason}")
    if ip_address:
        logger.warning(f"IP: {ip_address}")
    if user_id:
        logger.warning(f"User ID: {user_id}")
    logger.warning(f"Description (first 500 chars):")
    logger.warning(description[:500])
    logger.warning("=" * 80)

    # TODO: In production, also save to database for review/analytics
    # Example:
    # db.blocked_attempts.insert({
    #     "timestamp": timestamp,
    #     "reason": reason,
    #     "ip_address": ip_address,
    #     "user_id": user_id,
    #     "description": description[:1000]
    # })

"""
Input sanitization and validation utilities.

Provides secure input handling to protect against injection attacks
and malformed data.

Usage:
    from app.production.sanitization import (
        sanitize_string,
        sanitize_html,
        validate_email,
        validate_phone_malaysia,
        Sanitizer
    )

    clean_name = sanitize_string(user_input, max_length=100)
    clean_html = sanitize_html(html_content)
    is_valid = validate_email(email_input)
"""

import html
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Pattern, Set, Union

from loguru import logger


@dataclass
class SanitizationConfig:
    """Configuration for string sanitization."""

    # Maximum string length (0 = unlimited)
    max_length: int = 10000

    # Strip whitespace from ends
    strip_whitespace: bool = True

    # Normalize unicode (NFC, NFKC, NFD, NFKD, or None)
    unicode_normalize: Optional[str] = "NFC"

    # Remove null bytes
    remove_null_bytes: bool = True

    # Remove control characters (except newlines/tabs)
    remove_control_chars: bool = True

    # Allowed control characters when removing
    allowed_control_chars: Set[str] = field(default_factory=lambda: {"\n", "\r", "\t"})

    # Replace multiple whitespace with single space
    collapse_whitespace: bool = False

    # Convert to lowercase
    lowercase: bool = False


def sanitize_string(
    value: Any,
    config: Optional[SanitizationConfig] = None,
    max_length: int = 0,
    strip: bool = True,
    collapse_whitespace: bool = False,
    lowercase: bool = False
) -> str:
    """
    Sanitize a string value.

    Args:
        value: Input value to sanitize
        config: Full sanitization config (overrides other args)
        max_length: Maximum output length (0 = unlimited)
        strip: Strip leading/trailing whitespace
        collapse_whitespace: Replace multiple spaces with one
        lowercase: Convert to lowercase

    Returns:
        Sanitized string
    """
    if config is None:
        config = SanitizationConfig(
            max_length=max_length,
            strip_whitespace=strip,
            collapse_whitespace=collapse_whitespace,
            lowercase=lowercase,
        )

    # Convert to string
    if value is None:
        return ""

    text = str(value)

    # Remove null bytes
    if config.remove_null_bytes:
        text = text.replace("\x00", "")

    # Remove control characters
    if config.remove_control_chars:
        text = "".join(
            c for c in text
            if not unicodedata.category(c).startswith("C")
            or c in config.allowed_control_chars
        )

    # Normalize unicode
    if config.unicode_normalize:
        text = unicodedata.normalize(config.unicode_normalize, text)

    # Strip whitespace
    if config.strip_whitespace:
        text = text.strip()

    # Collapse whitespace
    if config.collapse_whitespace:
        text = re.sub(r"\s+", " ", text)

    # Lowercase
    if config.lowercase:
        text = text.lower()

    # Truncate to max length
    if config.max_length > 0 and len(text) > config.max_length:
        text = text[:config.max_length]

    return text


# HTML sanitization patterns
_SCRIPT_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_STYLE_PATTERN = re.compile(r"<style[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
_EVENT_HANDLER_PATTERN = re.compile(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', re.IGNORECASE)
_JAVASCRIPT_URL_PATTERN = re.compile(r'javascript\s*:', re.IGNORECASE)

# Allowed HTML tags (configurable)
DEFAULT_ALLOWED_TAGS = {
    "p", "br", "strong", "em", "u", "s", "a", "ul", "ol", "li",
    "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "code",
    "span", "div", "img", "table", "thead", "tbody", "tr", "th", "td",
}

DEFAULT_ALLOWED_ATTRS = {
    "a": {"href", "title", "target", "rel"},
    "img": {"src", "alt", "title", "width", "height"},
    "*": {"class", "id", "style"},
}


def sanitize_html(
    html_content: str,
    allowed_tags: Optional[Set[str]] = None,
    allowed_attrs: Optional[Dict[str, Set[str]]] = None,
    strip_scripts: bool = True,
    strip_styles: bool = True,
    strip_event_handlers: bool = True,
    escape_remaining: bool = True
) -> str:
    """
    Sanitize HTML content to prevent XSS attacks.

    This is a basic sanitizer. For production with rich HTML,
    consider using a library like bleach or html-sanitizer.

    Args:
        html_content: HTML string to sanitize
        allowed_tags: Tags to preserve (None = escape all)
        allowed_attrs: Allowed attributes per tag
        strip_scripts: Remove script tags
        strip_styles: Remove style tags
        strip_event_handlers: Remove onclick, onload, etc.
        escape_remaining: HTML escape non-allowed content

    Returns:
        Sanitized HTML string
    """
    if not html_content:
        return ""

    text = str(html_content)

    # Remove script tags
    if strip_scripts:
        text = _SCRIPT_PATTERN.sub("", text)

    # Remove style tags
    if strip_styles:
        text = _STYLE_PATTERN.sub("", text)

    # Remove event handlers
    if strip_event_handlers:
        text = _EVENT_HANDLER_PATTERN.sub("", text)

    # Remove javascript: URLs
    text = _JAVASCRIPT_URL_PATTERN.sub("", text)

    # If no allowed tags, escape everything
    if allowed_tags is None and escape_remaining:
        return html.escape(text)

    # For basic sanitization without full parsing
    # Note: For production, use a proper HTML parser like bleach
    if escape_remaining:
        # This is a simplified approach - escape first, then unescape allowed tags
        # A proper implementation would use an HTML parser
        text = html.escape(text)

    return text


def escape_html(text: str) -> str:
    """
    Escape HTML special characters.

    Converts: < > & " ' to their HTML entities.
    """
    return html.escape(text, quote=True)


def unescape_html(text: str) -> str:
    """Unescape HTML entities back to characters."""
    return html.unescape(text)


# Validation patterns
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)

# Malaysian phone number patterns
MALAYSIA_PHONE_PATTERN = re.compile(
    r"^(\+?60|0)?(1[0-9]{8,9}|[3-9][0-9]{7,8})$"
)

URL_PATTERN = re.compile(
    r"^https?://[^\s/$.?#].[^\s]*$",
    re.IGNORECASE
)

SUBDOMAIN_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$|^[a-z0-9]$"
)

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)


def validate_email(email: str) -> bool:
    """
    Validate email address format.

    Returns True if valid, False otherwise.
    """
    if not email or len(email) > 254:
        return False
    return bool(EMAIL_PATTERN.match(email.strip()))


def validate_phone_malaysia(phone: str) -> bool:
    """
    Validate Malaysian phone number format.

    Accepts formats:
    - +60123456789
    - 60123456789
    - 0123456789
    - 123456789

    Returns True if valid, False otherwise.
    """
    if not phone:
        return False
    # Remove spaces, dashes, parentheses
    cleaned = re.sub(r"[\s\-\(\)]", "", phone)
    return bool(MALAYSIA_PHONE_PATTERN.match(cleaned))


def normalize_phone_malaysia(phone: str) -> Optional[str]:
    """
    Normalize Malaysian phone number to +60 format.

    Returns None if invalid.
    """
    if not validate_phone_malaysia(phone):
        return None

    cleaned = re.sub(r"[\s\-\(\)]", "", phone)

    # Remove leading + if present
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]

    # Add 60 prefix if missing
    if cleaned.startswith("0"):
        cleaned = "6" + cleaned
    elif not cleaned.startswith("60"):
        cleaned = "60" + cleaned

    return "+" + cleaned


def validate_url(url: str) -> bool:
    """Validate URL format."""
    if not url or len(url) > 2048:
        return False
    return bool(URL_PATTERN.match(url.strip()))


def validate_subdomain(subdomain: str) -> bool:
    """
    Validate subdomain format.

    Rules:
    - 1-63 characters
    - Alphanumeric and hyphens only
    - Cannot start or end with hyphen
    """
    if not subdomain or len(subdomain) > 63:
        return False
    return bool(SUBDOMAIN_PATTERN.match(subdomain.lower()))


def validate_uuid(uuid_str: str) -> bool:
    """Validate UUID format."""
    if not uuid_str:
        return False
    return bool(UUID_PATTERN.match(uuid_str.strip()))


class Sanitizer:
    """
    Comprehensive sanitizer for request data.

    Provides type-specific sanitization and validation
    for common input fields.
    """

    @staticmethod
    def string(
        value: Any,
        max_length: int = 10000,
        strip: bool = True,
        allow_empty: bool = True
    ) -> Optional[str]:
        """Sanitize string input."""
        if value is None:
            return None if allow_empty else ""

        result = sanitize_string(value, max_length=max_length, strip=strip)

        if not allow_empty and not result:
            return None

        return result

    @staticmethod
    def email(value: Any) -> Optional[str]:
        """Sanitize and validate email."""
        if not value:
            return None

        email = sanitize_string(value, max_length=254, lowercase=True)

        if validate_email(email):
            return email

        return None

    @staticmethod
    def phone_malaysia(value: Any, normalize: bool = True) -> Optional[str]:
        """Sanitize and validate Malaysian phone number."""
        if not value:
            return None

        phone = sanitize_string(value, max_length=20)

        if normalize:
            return normalize_phone_malaysia(phone)

        return phone if validate_phone_malaysia(phone) else None

    @staticmethod
    def url(value: Any) -> Optional[str]:
        """Sanitize and validate URL."""
        if not value:
            return None

        url = sanitize_string(value, max_length=2048, strip=True)

        if validate_url(url):
            return url

        return None

    @staticmethod
    def subdomain(value: Any) -> Optional[str]:
        """Sanitize and validate subdomain."""
        if not value:
            return None

        subdomain = sanitize_string(value, max_length=63, lowercase=True)
        subdomain = re.sub(r"[^a-z0-9-]", "", subdomain)

        if validate_subdomain(subdomain):
            return subdomain

        return None

    @staticmethod
    def uuid(value: Any) -> Optional[str]:
        """Sanitize and validate UUID."""
        if not value:
            return None

        uuid_str = sanitize_string(value, max_length=36, strip=True, lowercase=True)

        if validate_uuid(uuid_str):
            return uuid_str

        return None

    @staticmethod
    def html(value: Any, max_length: int = 100000) -> str:
        """Sanitize HTML content."""
        if not value:
            return ""

        text = str(value)
        if len(text) > max_length:
            text = text[:max_length]

        return sanitize_html(text)

    @staticmethod
    def integer(
        value: Any,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        default: Optional[int] = None
    ) -> Optional[int]:
        """Sanitize integer input."""
        if value is None:
            return default

        try:
            result = int(value)

            if min_value is not None and result < min_value:
                return min_value
            if max_value is not None and result > max_value:
                return max_value

            return result
        except (ValueError, TypeError):
            return default

    @staticmethod
    def decimal(
        value: Any,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        precision: int = 2,
        default: Optional[float] = None
    ) -> Optional[float]:
        """Sanitize decimal/float input."""
        if value is None:
            return default

        try:
            result = round(float(value), precision)

            if min_value is not None and result < min_value:
                return min_value
            if max_value is not None and result > max_value:
                return max_value

            return result
        except (ValueError, TypeError):
            return default

    @staticmethod
    def boolean(value: Any, default: bool = False) -> bool:
        """Sanitize boolean input."""
        if value is None:
            return default

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")

        return bool(value)


# SQL injection prevention helpers (for raw queries if needed)
def escape_sql_like(value: str) -> str:
    """
    Escape special characters for SQL LIKE queries.

    Note: Prefer parameterized queries. Use this only for
    dynamic LIKE patterns where parameterization isn't possible.
    """
    return (
        value
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def is_safe_identifier(value: str) -> bool:
    """
    Check if value is safe to use as SQL identifier.

    Only allows alphanumeric and underscore.
    """
    return bool(re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", value))

"""
BinaApp Subscription Limits Configuration

Pricing Tiers:
- Starter: RM5/month
- Basic: RM29/month
- Pro: RM49/month

None values indicate unlimited usage.
"""

from typing import Dict, Any, Optional

SUBSCRIPTION_LIMITS: Dict[str, Dict[str, Any]] = {
    'starter': {
        'price': 5.00,
        'websites': 1,
        'menu_items': 20,
        'ai_hero_generations': 1,
        'ai_menu_images': 5,
        'delivery_zones': 1,
        'riders': 0,
        'monthly_reset': False,  # Lifetime limits for Starter
    },
    'basic': {
        'price': 29.00,
        'websites': 5,
        'menu_items': None,  # Unlimited
        'ai_hero_generations': 10,
        'ai_menu_images': 30,
        'delivery_zones': 5,
        'riders': 0,
        'monthly_reset': True,  # AI limits reset monthly
    },
    'pro': {
        'price': 49.00,
        'websites': None,  # Unlimited
        'menu_items': None,  # Unlimited
        'ai_hero_generations': None,  # Unlimited
        'ai_menu_images': None,  # Unlimited
        'delivery_zones': None,  # Unlimited
        'riders': 10,
        'monthly_reset': True,  # Limits reset monthly
    }
}

ADDON_PRICES: Dict[str, float] = {
    'website': 15.00,        # Additional website slot
    'delivery_zone': 5.00,   # Additional delivery zone
    'ai_hero': 2.00,         # Single AI hero generation
    'ai_image': 1.00,        # Single AI menu image
    'rider': 10.00,          # Additional rider slot
}


def get_tier_limits(tier: str) -> Optional[Dict[str, Any]]:
    """
    Get the limits configuration for a subscription tier.

    Args:
        tier: The subscription tier name ('starter', 'basic', 'pro')

    Returns:
        Dict with tier limits or None if tier doesn't exist
    """
    return SUBSCRIPTION_LIMITS.get(tier.lower())


def get_addon_price(addon_type: str) -> Optional[float]:
    """
    Get the price for an addon type.

    Args:
        addon_type: The addon type name

    Returns:
        Price in RM or None if addon doesn't exist
    """
    return ADDON_PRICES.get(addon_type.lower())


def is_unlimited(tier: str, resource: str) -> bool:
    """
    Check if a resource is unlimited for a given tier.

    Args:
        tier: The subscription tier name
        resource: The resource name (e.g., 'websites', 'menu_items')

    Returns:
        True if unlimited (None), False otherwise
    """
    limits = get_tier_limits(tier)
    if limits is None:
        return False
    return limits.get(resource) is None


def get_tier_price(tier: str, billing_cycle: str = 'monthly') -> Optional[float]:
    """
    Get the price for a subscription tier.

    Args:
        tier: The subscription tier name
        billing_cycle: 'monthly' or 'yearly'

    Returns:
        Price in RM or None if tier doesn't exist
    """
    limits = get_tier_limits(tier)
    if limits is None:
        return None

    monthly_price = limits['price']

    if billing_cycle == 'yearly':
        # 2 months free for yearly billing (10 months price)
        return monthly_price * 10

    return monthly_price

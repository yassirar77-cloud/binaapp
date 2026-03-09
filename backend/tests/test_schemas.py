"""
Tests for Pydantic schema validation — schemas.py, delivery_schemas.py, dispute_schemas.py.

Covers:
- Valid data acceptance
- Required field enforcement
- Field validators (subdomain, price, password length, email)
- Enum values completeness
"""

import pytest
from datetime import datetime
from decimal import Decimal
from pydantic import ValidationError


# =============================================================================
# Core Schemas (app.models.schemas)
# =============================================================================

class TestUserSchemas:
    def test_user_create_valid(self):
        from app.models.schemas import UserCreate

        user = UserCreate(email="test@example.com", password="secure12", full_name="Test")
        assert user.email == "test@example.com"

    def test_user_create_short_password(self):
        from app.models.schemas import UserCreate

        with pytest.raises(ValidationError) as exc_info:
            UserCreate(email="test@example.com", password="short")
        assert "min_length" in str(exc_info.value).lower() or "at least" in str(exc_info.value).lower()

    def test_user_create_invalid_email(self):
        from app.models.schemas import UserCreate

        with pytest.raises(ValidationError):
            UserCreate(email="not-email", password="securepass")

    def test_user_login_valid(self):
        from app.models.schemas import UserLogin

        login = UserLogin(email="test@example.com", password="anypass")
        assert login.email == "test@example.com"

    def test_user_response_with_all_fields(self):
        from app.models.schemas import UserResponse, SubscriptionTier

        user = UserResponse(
            id="user-1",
            email="test@example.com",
            full_name="Test User",
            created_at=datetime.utcnow(),
            subscription_tier=SubscriptionTier.FREE,
            websites_count=3,
        )
        assert user.websites_count == 3


class TestWebsiteGenerationRequest:
    def test_valid_request(self):
        from app.models.schemas import WebsiteGenerationRequest, Language

        req = WebsiteGenerationRequest(
            description="A restaurant serving Malaysian food in Kuala Lumpur",
            language=Language.MALAY,
            business_name="Kedai Makan",
            subdomain="kedaimakan",
        )
        assert req.subdomain == "kedaimakan"

    def test_description_too_short(self):
        from app.models.schemas import WebsiteGenerationRequest

        with pytest.raises(ValidationError):
            WebsiteGenerationRequest(
                description="Short",  # Less than min_length=10
                business_name="Kedai",
                subdomain="kedai",
            )

    def test_business_name_too_short(self):
        from app.models.schemas import WebsiteGenerationRequest

        with pytest.raises(ValidationError):
            WebsiteGenerationRequest(
                description="A long enough description for validation",
                business_name="K",  # Less than min_length=2
                subdomain="kedai",
            )

    def test_subdomain_too_short(self):
        from app.models.schemas import WebsiteGenerationRequest

        with pytest.raises(ValidationError):
            WebsiteGenerationRequest(
                description="A long enough description for validation",
                business_name="Kedai Makan",
                subdomain="ab",  # Less than min_length=3
            )

    def test_subdomain_invalid_characters(self):
        from app.models.schemas import WebsiteGenerationRequest

        with pytest.raises(ValidationError):
            WebsiteGenerationRequest(
                description="A long enough description for validation",
                business_name="Kedai Makan",
                subdomain="INVALID_UPPER",
            )

    def test_subdomain_with_hyphens_valid(self):
        from app.models.schemas import WebsiteGenerationRequest

        req = WebsiteGenerationRequest(
            description="A long enough description for validation",
            business_name="Kedai Makan",
            subdomain="kedai-makan-kl",
        )
        assert req.subdomain == "kedai-makan-kl"

    def test_subdomain_starting_with_hyphen_invalid(self):
        from app.models.schemas import WebsiteGenerationRequest

        with pytest.raises(ValidationError):
            WebsiteGenerationRequest(
                description="A long enough description for validation",
                business_name="Kedai Makan",
                subdomain="-kedai",
            )

    def test_optional_fields_default(self):
        from app.models.schemas import WebsiteGenerationRequest

        req = WebsiteGenerationRequest(
            description="A long enough description for validation",
            business_name="Kedai Makan",
            subdomain="kedai",
        )
        assert req.include_whatsapp is True
        assert req.include_maps is True
        assert req.include_ecommerce is False
        assert req.color_mode == "light"
        assert req.uploaded_images == []


class TestCheckoutSessionRequest:
    def test_valid_monthly(self):
        from app.models.schemas import CheckoutSessionRequest, SubscriptionTier

        req = CheckoutSessionRequest(tier=SubscriptionTier.BASIC, billing_period="monthly")
        assert req.billing_period == "monthly"

    def test_valid_yearly(self):
        from app.models.schemas import CheckoutSessionRequest, SubscriptionTier

        req = CheckoutSessionRequest(tier=SubscriptionTier.PRO, billing_period="yearly")
        assert req.billing_period == "yearly"

    def test_invalid_billing_period(self):
        from app.models.schemas import CheckoutSessionRequest, SubscriptionTier

        with pytest.raises(ValidationError):
            CheckoutSessionRequest(tier=SubscriptionTier.BASIC, billing_period="weekly")


class TestMenuItemSchema:
    def test_valid_menu_item(self):
        from app.models.schemas import MenuItemCreate

        item = MenuItemCreate(
            name="Nasi Lemak",
            price=8.50,
            website_id="site-1",
        )
        assert item.price == 8.50

    def test_negative_price_rejected(self):
        from app.models.schemas import MenuItemCreate

        with pytest.raises(ValidationError):
            MenuItemCreate(
                name="Bad Item",
                price=-5.00,
                website_id="site-1",
            )

    def test_zero_price_allowed(self):
        from app.models.schemas import MenuItemCreate

        item = MenuItemCreate(name="Free Item", price=0, website_id="site-1")
        assert item.price == 0


class TestEnums:
    def test_website_status_values(self):
        from app.models.schemas import WebsiteStatus

        expected = {"draft", "generating", "published", "failed"}
        actual = {s.value for s in WebsiteStatus}
        assert expected == actual

    def test_subscription_tier_values(self):
        from app.models.schemas import SubscriptionTier

        expected = {"free", "basic", "pro", "enterprise"}
        actual = {s.value for s in SubscriptionTier}
        assert expected == actual

    def test_language_values(self):
        from app.models.schemas import Language

        expected = {"en", "ms"}
        actual = {s.value for s in Language}
        assert expected == actual


# =============================================================================
# Delivery Schemas (app.models.delivery_schemas)
# =============================================================================

class TestDeliverySchemas:
    def test_order_status_values(self):
        from app.models.delivery_schemas import OrderStatus

        expected = {
            "pending", "confirmed", "assigned", "preparing", "ready",
            "picked_up", "delivering", "delivered", "completed",
            "cancelled", "rejected",
        }
        actual = {s.value for s in OrderStatus}
        assert expected == actual

    def test_payment_method_values(self):
        from app.models.delivery_schemas import PaymentMethod

        expected = {"cod", "online", "ewallet"}
        actual = {s.value for s in PaymentMethod}
        assert expected == actual

    def test_payment_status_values(self):
        from app.models.delivery_schemas import PaymentStatus

        expected = {"pending", "paid", "failed", "refunded"}
        actual = {s.value for s in PaymentStatus}
        assert expected == actual

    def test_delivery_zone_defaults(self):
        from app.models.delivery_schemas import DeliveryZoneBase

        zone = DeliveryZoneBase(zone_name="Zone A")
        assert zone.delivery_fee == Decimal("5.00")
        assert zone.minimum_order == Decimal("20.00")
        assert zone.estimated_time_min == 30
        assert zone.estimated_time_max == 45
        assert zone.is_active is True

    def test_delivery_zone_negative_fee_rejected(self):
        from app.models.delivery_schemas import DeliveryZoneBase

        with pytest.raises(ValidationError):
            DeliveryZoneBase(zone_name="Bad Zone", delivery_fee=Decimal("-1.00"))


# =============================================================================
# Dispute Schemas (app.models.dispute_schemas)
# =============================================================================

class TestDisputeSchemas:
    def test_dispute_category_values(self):
        from app.models.dispute_schemas import DisputeCategory

        # Check a few critical categories exist
        values = {c.value for c in DisputeCategory}
        assert "wrong_items" in values
        assert "missing_items" in values
        assert "never_delivered" in values
        assert "payment_issue" in values

    def test_dispute_status_values(self):
        from app.models.dispute_schemas import DisputeStatus

        expected = {"open", "under_review", "awaiting_response", "resolved", "closed", "escalated", "rejected"}
        actual = {s.value for s in DisputeStatus}
        assert expected == actual

    def test_dispute_priority_values(self):
        from app.models.dispute_schemas import DisputePriority

        expected = {"low", "medium", "high", "urgent"}
        actual = {s.value for s in DisputePriority}
        assert expected == actual

    def test_message_sender_includes_ai(self):
        from app.models.dispute_schemas import DisputeMessageSender

        values = {s.value for s in DisputeMessageSender}
        assert "ai" in values
        assert "customer" in values
        assert "system" in values

"""
Basic health check tests for CI.
These tests verify the app can be imported without errors.
"""


def test_app_imports():
    """Test that the main app module can be imported."""
    from app.main import app
    assert app is not None


def test_app_has_routes():
    """Test that the app has registered routes."""
    from app.main import app
    assert len(app.routes) > 0


def test_schemas_import():
    """Test that schema modules can be imported."""
    from app.models.schemas import Language, WebsiteStatus
    assert Language is not None
    assert WebsiteStatus is not None


def test_delivery_schemas_import():
    """Test that delivery schemas can be imported."""
    from app.models.delivery_schemas import OrderStatus, PaymentMethod
    assert OrderStatus is not None
    assert PaymentMethod is not None

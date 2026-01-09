"""
Pydantic schemas for BinaApp Delivery System
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from decimal import Decimal


# =====================================================
# ENUMS
# =====================================================

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    PICKED_UP = "picked_up"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class PaymentMethod(str, Enum):
    COD = "cod"  # Cash on Delivery
    ONLINE = "online"
    EWALLET = "ewallet"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class VehicleType(str, Enum):
    MOTORCYCLE = "motorcycle"
    BICYCLE = "bicycle"
    CAR = "car"


# =====================================================
# DELIVERY ZONE SCHEMAS
# =====================================================

class DeliveryZoneBase(BaseModel):
    zone_name: str
    zone_polygon: Optional[Dict[str, Any]] = None  # GeoJSON
    # Circle-based zone (for Leaflet map display)
    center_lat: Optional[Decimal] = None  # Zone center latitude
    center_lng: Optional[Decimal] = None  # Zone center longitude
    radius_km: Optional[Decimal] = Field(default=Decimal("5.0"), ge=0)  # Radius in km
    delivery_fee: Decimal = Field(default=Decimal("5.00"), ge=0)
    minimum_order: Decimal = Field(default=Decimal("20.00"), ge=0)
    estimated_time_min: int = Field(default=30, ge=0)
    estimated_time_max: int = Field(default=45, ge=0)
    is_active: bool = True
    sort_order: int = 0


class DeliveryZoneCreate(DeliveryZoneBase):
    website_id: str


class DeliveryZoneUpdate(BaseModel):
    zone_name: Optional[str] = None
    zone_polygon: Optional[Dict[str, Any]] = None
    # Circle-based zone (for Leaflet map display)
    center_lat: Optional[Decimal] = None
    center_lng: Optional[Decimal] = None
    radius_km: Optional[Decimal] = None
    delivery_fee: Optional[Decimal] = None
    minimum_order: Optional[Decimal] = None
    estimated_time_min: Optional[int] = None
    estimated_time_max: Optional[int] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class DeliveryZoneResponse(DeliveryZoneBase):
    id: str
    website_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# MENU SCHEMAS
# =====================================================

class MenuCategoryBase(BaseModel):
    name: str
    name_en: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True


class MenuCategoryCreate(MenuCategoryBase):
    website_id: str


class MenuCategoryResponse(MenuCategoryBase):
    id: str
    website_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class MenuItemOptionBase(BaseModel):
    option_group: str  # e.g., "Size", "Add-ons"
    option_name: str
    price_modifier: Decimal = Decimal("0.00")
    is_default: bool = False
    sort_order: int = 0


class MenuItemOptionResponse(MenuItemOptionBase):
    id: str
    menu_item_id: str

    class Config:
        from_attributes = True


class MenuItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal = Field(gt=0)
    image_url: Optional[str] = None
    is_available: bool = True
    is_popular: bool = False
    preparation_time: int = Field(default=15, ge=0)  # minutes
    sort_order: int = 0


class MenuItemCreate(MenuItemBase):
    website_id: str
    category_id: Optional[str] = None


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    image_url: Optional[str] = None
    category_id: Optional[str] = None
    is_available: Optional[bool] = None
    is_popular: Optional[bool] = None
    preparation_time: Optional[int] = None
    sort_order: Optional[int] = None


class MenuItemResponse(MenuItemBase):
    id: str
    website_id: str
    category_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    options: List[MenuItemOptionResponse] = []

    class Config:
        from_attributes = True


class MenuResponse(BaseModel):
    categories: List[MenuCategoryResponse]
    items: List[MenuItemResponse]


# =====================================================
# ORDER SCHEMAS
# =====================================================

class OrderItemCreate(BaseModel):
    menu_item_id: str
    quantity: int = Field(ge=1)
    options: Optional[Dict[str, Any]] = None
    notes: str = ""

    @field_validator('notes', mode='before')
    @classmethod
    def convert_none_to_empty(cls, v):
        """Convert None to empty string for notes field"""
        return "" if v is None else str(v)


class OrderItemResponse(BaseModel):
    id: str
    order_id: str
    menu_item_id: Optional[str]
    item_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    options: Optional[Dict[str, Any]]
    notes: Optional[str]

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    website_id: str
    customer_name: str = ""
    customer_phone: str = ""
    customer_email: str = ""
    delivery_address: str = ""
    delivery_latitude: Optional[Decimal] = None
    delivery_longitude: Optional[Decimal] = None
    delivery_notes: str = ""
    delivery_zone_id: Optional[str] = None
    items: List[OrderItemCreate] = Field(min_length=1)
    payment_method: PaymentMethod = PaymentMethod.COD

    @field_validator('customer_email', 'delivery_notes', mode='before')
    @classmethod
    def convert_none_to_empty(cls, v):
        """Convert None to empty string for optional string fields"""
        return "" if v is None else str(v)

    @field_validator('delivery_zone_id', mode='before')
    @classmethod
    def validate_zone_id(cls, v):
        """Convert empty string or None to None for optional UUID field"""
        if v == '' or v is None:
            return None
        return str(v)

    @field_validator('customer_name', 'delivery_address')
    @classmethod
    def validate_required_strings(cls, v, info):
        """Ensure required string fields are not empty"""
        if not v or not v.strip():
            field_names = {
                'customer_name': 'Nama pelanggan',
                'delivery_address': 'Alamat penghantaran'
            }
            raise ValueError(f'{field_names.get(info.field_name, info.field_name)} diperlukan')
        return v.strip()

    @field_validator('customer_phone')
    @classmethod
    def validate_phone(cls, v):
        """Validate and format phone number"""
        if not v or not v.strip():
            raise ValueError('Nombor telefon diperlukan')
        # Basic phone validation
        phone = v.strip().replace(' ', '').replace('-', '')
        if not phone.startswith('+'):
            phone = '+60' + phone.lstrip('0')  # Assume Malaysia
        return phone


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    notes: Optional[str] = None


class OrderStatusHistoryResponse(BaseModel):
    id: str
    order_id: str
    status: str
    notes: Optional[str]
    updated_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class RiderLocationResponse(BaseModel):
    latitude: Decimal
    longitude: Decimal
    recorded_at: datetime

    class Config:
        from_attributes = True


class RiderInfoResponse(BaseModel):
    id: str
    name: str
    phone: str
    photo_url: Optional[str]
    vehicle_type: Optional[str]
    vehicle_plate: Optional[str]
    rating: Decimal
    current_latitude: Optional[Decimal]
    current_longitude: Optional[Decimal]

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: str
    order_number: str
    website_id: str
    customer_name: str
    customer_phone: str
    customer_email: Optional[str]
    delivery_address: str
    delivery_latitude: Optional[Decimal]
    delivery_longitude: Optional[Decimal]
    delivery_notes: Optional[str]
    delivery_zone_id: Optional[str]
    delivery_fee: Decimal
    subtotal: Decimal
    total_amount: Decimal
    payment_method: str
    payment_status: str
    payment_reference: Optional[str]
    status: str
    created_at: datetime
    confirmed_at: Optional[datetime]
    preparing_at: Optional[datetime]
    ready_at: Optional[datetime]
    picked_up_at: Optional[datetime]
    delivered_at: Optional[datetime]
    completed_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    rider_id: Optional[str]
    estimated_prep_time: Optional[int]
    estimated_delivery_time: Optional[int]
    actual_delivery_time: Optional[int]

    class Config:
        from_attributes = True


class OrderTrackingResponse(BaseModel):
    order: OrderResponse
    items: List[OrderItemResponse]
    status_history: List[OrderStatusHistoryResponse]
    rider: Optional[RiderInfoResponse] = None
    rider_location: Optional[RiderLocationResponse] = None
    eta_minutes: Optional[int] = None


# =====================================================
# COVERAGE CHECK SCHEMAS
# =====================================================

class CoverageCheckRequest(BaseModel):
    website_id: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    address: Optional[str] = None

    @field_validator('latitude', 'longitude', 'address')
    @classmethod
    def check_location_data(cls, v, info):
        # Either lat/lng OR address must be provided
        # Note: In Pydantic V2, we can't access other field values in field_validator
        # This validation is simplified - consider using model_validator for cross-field validation
        return v


class CoverageCheckResponse(BaseModel):
    covered: bool
    zone: Optional[DeliveryZoneResponse] = None
    fee: Optional[Decimal] = None
    estimated_time: Optional[str] = None
    message: Optional[str] = None


# =====================================================
# RIDER SCHEMAS
# =====================================================

class RiderBase(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    photo_url: Optional[str] = None
    vehicle_type: Optional[VehicleType] = None
    vehicle_plate: Optional[str] = None
    vehicle_model: Optional[str] = None
    is_active: bool = True


class RiderCreate(RiderBase):
    website_id: Optional[str] = None  # Null for shared riders
    password: str = Field(min_length=6)


class RiderUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    photo_url: Optional[str] = None
    vehicle_type: Optional[VehicleType] = None
    vehicle_plate: Optional[str] = None
    vehicle_model: Optional[str] = None
    is_active: Optional[bool] = None


class RiderResponse(RiderBase):
    id: str
    website_id: Optional[str]
    is_online: bool
    current_latitude: Optional[Decimal]
    current_longitude: Optional[Decimal]
    last_location_update: Optional[datetime]
    total_deliveries: int
    rating: Decimal
    total_ratings: int
    created_at: datetime

    class Config:
        from_attributes = True


class RiderLocationUpdate(BaseModel):
    latitude: Decimal
    longitude: Decimal


class RiderStatusUpdate(BaseModel):
    is_online: bool


class RiderCreateBusiness(RiderBase):
    """
    Phase 1 (Business Dashboard) rider creation payload.

    We do not activate rider authentication / rider app yet (Phase 2),
    so this schema intentionally omits password/auth fields.
    """


class AssignRiderRequest(BaseModel):
    rider_id: Optional[str] = None


# =====================================================
# DELIVERY SETTINGS SCHEMAS
# =====================================================

class DeliveryHoursDay(BaseModel):
    open: str  # e.g., "09:00"
    close: str  # e.g., "22:00"
    closed: bool = False


class DeliverySettingsBase(BaseModel):
    delivery_hours: Optional[Dict[str, DeliveryHoursDay]] = None
    minimum_order: Decimal = Decimal("20.00")
    max_delivery_distance: Decimal = Decimal("10.00")  # km
    auto_accept_orders: bool = False
    notify_whatsapp: bool = True
    notify_email: bool = False
    notify_sound: bool = True
    whatsapp_number: Optional[str] = None
    accept_cod: bool = True
    accept_online: bool = False
    accept_ewallet: bool = False
    use_own_riders: bool = True


class DeliverySettingsCreate(DeliverySettingsBase):
    website_id: str


class DeliverySettingsUpdate(BaseModel):
    delivery_hours: Optional[Dict[str, Any]] = None
    minimum_order: Optional[Decimal] = None
    max_delivery_distance: Optional[Decimal] = None
    auto_accept_orders: Optional[bool] = None
    notify_whatsapp: Optional[bool] = None
    notify_email: Optional[bool] = None
    notify_sound: Optional[bool] = None
    whatsapp_number: Optional[str] = None
    accept_cod: Optional[bool] = None
    accept_online: Optional[bool] = None
    accept_ewallet: Optional[bool] = None
    use_own_riders: Optional[bool] = None


class DeliverySettingsResponse(DeliverySettingsBase):
    id: str
    website_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# ZONES WITH SETTINGS RESPONSE
# =====================================================

class ZonesWithSettingsResponse(BaseModel):
    zones: List[DeliveryZoneResponse]
    settings: Optional[DeliverySettingsResponse]

from pydantic import BaseModel, Field
from typing import List, Optional


class Location(BaseModel):
    address: str = ""
    lat: float
    lng: float
    city: Optional[str] = ""
    area: Optional[str] = ""
    country: Optional[str] = ""


class OtpRequest(BaseModel):
    phone: str
    role: str  # customer | driver | provider
    name: Optional[str] = None


class OtpVerify(BaseModel):
    phone: str
    code: str
    role: str
    name: Optional[str] = None


class AdminLogin(BaseModel):
    email: str
    password: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    company_name: Optional[str] = None
    cr_number: Optional[str] = None
    service_areas: Optional[List[str]] = None
    vehicle: Optional[dict] = None


class DocumentSubmit(BaseModel):
    documents: List[dict]  # [{type, reference, expiry}]
    vehicle: Optional[dict] = None


class ShipmentCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    category: Optional[str] = ""
    category_key: Optional[str] = ""
    quantity: Optional[str] = ""
    weight: Optional[str] = ""
    weight_unit: Optional[str] = "kg"
    packages: Optional[str] = ""
    dimensions: Optional[str] = ""
    fragile: Optional[bool] = False
    images: Optional[List[str]] = []
    pickup_location: Optional[Location] = None
    delivery_location: Optional[Location] = None
    pickup_date: Optional[str] = ""
    pickup_time: Optional[str] = ""
    delivery_date: Optional[str] = ""
    delivery_time: Optional[str] = ""
    vehicle_type: Optional[str] = ""
    required_capacity: Optional[str] = ""
    loading_service: Optional[bool] = False
    unloading_service: Optional[bool] = False
    special_instructions: Optional[str] = ""
    expected_price: Optional[str] = ""
    status: Optional[str] = "DRAFT"  # DRAFT or PUBLISHED


class BidCreate(BaseModel):
    price: float
    note: Optional[str] = ""


class TripStatusUpdate(BaseModel):
    status: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    pod_photo: Optional[str] = None
    pod_notes: Optional[str] = ""


class DeliveryConfirm(BaseModel):
    reference: Optional[str] = ""
    lat: Optional[float] = None
    lng: Optional[float] = None
    delivered_to_name: Optional[str] = ""


class DisputeCreate(BaseModel):
    reason: str
    notes: Optional[str] = ""


class ReviewCreate(BaseModel):
    overall: int = Field(ge=1, le=5)
    service_quality: int = Field(ge=1, le=5)
    communication: int = Field(ge=1, le=5)
    on_time: int = Field(ge=1, le=5)
    comment: Optional[str] = ""


class VerifyAction(BaseModel):
    action: str  # approve | reject | suspend | request_changes
    notes: Optional[str] = ""

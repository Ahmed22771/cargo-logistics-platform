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
    customer_max_offer: Optional[float] = None
    status: Optional[str] = "DRAFT"  # DRAFT or PUBLISHED


class PricingQuoteBody(BaseModel):
    pickup_location: Optional[Location] = None
    delivery_location: Optional[Location] = None
    vehicle_type: Optional[str] = ""
    fragile: Optional[bool] = False
    loading_service: Optional[bool] = False
    unloading_service: Optional[bool] = False


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


# ================ Company / Provider portal ================
class VehicleBody(BaseModel):
    plate_number: str
    vehicle_type: Optional[str] = ""
    make: Optional[str] = ""
    model: Optional[str] = ""
    year: Optional[str] = ""
    color: Optional[str] = ""
    capacity: Optional[str] = ""
    notes: Optional[str] = ""
    status: Optional[str] = "ACTIVE"  # ACTIVE | INACTIVE | MAINTENANCE
    assigned_driver_id: Optional[str] = None
    # Regulatory readiness (Oman). Free-form dict normalized server-side into a
    # known set of keys (operating card / chassis / barcode ...). Optional so old
    # clients that never send it keep working unchanged.
    regulatory: Optional[dict] = None


class VehicleAssignBody(BaseModel):
    driver_id: Optional[str] = None  # None to unassign


class ProviderLinkDriverBody(BaseModel):
    phone: str


class ProviderBidBody(BaseModel):
    driver_id: str
    price: float
    note: Optional[str] = ""


# ================ Regulatory readiness (Oman) ================
# NOTE: These models ONLY shape data so the platform can *store* regulatory
# information in future. They do NOT introduce any eligibility / block logic,
# Naql API integration, or real license issuance. All fields are optional and
# backward-compatible; absent fields simply remain empty.
class AppLicenseBody(BaseModel):
    """Smart Transport Application license (platform-level, single record)."""
    license_number: Optional[str] = ""
    license_type: Optional[str] = ""          # e.g. trucks / taxi / buses (per Naql)
    issuing_authority: Optional[str] = ""
    issue_date: Optional[str] = ""            # ISO date string
    expiry_date: Optional[str] = ""           # ISO date string
    status: Optional[str] = ""                # free-form, e.g. ACTIVE / EXPIRED / PENDING / ""
    document_id: Optional[str] = None         # -> Unified Documents record when available
    notes: Optional[str] = ""


class DriverRegulatoryBody(BaseModel):
    """Driver regulatory / licensing data (stored on the driver user document)."""
    driving_license_number: Optional[str] = ""
    license_class: Optional[str] = ""
    license_issue_date: Optional[str] = ""
    license_expiry_date: Optional[str] = ""
    license_status: Optional[str] = ""        # free-form, e.g. VALID / EXPIRED / ""
    driver_training_status: Optional[str] = ""
    driver_training_date: Optional[str] = ""
    regulatory_notes: Optional[str] = ""


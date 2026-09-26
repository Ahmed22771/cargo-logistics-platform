from pydantic import BaseModel, Field
from typing import List, Optional, Literal


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


# ================ Contracts & Competition ================
# These models add only the API/data contracts for the new B2B contract
# marketplace. They do not alter existing Shipment/Bid/Trip models.


class ContractCreate(BaseModel):
    """Create a master B2B transport contract."""

    title: str
    description: Optional[str] = ""

    # Optional link to an existing CARGO customer/company account.
    customer_id: Optional[str] = None
    customer_name: Optional[str] = ""

    contract_number: Optional[str] = ""

    # FULL = compete for the whole contract
    # SPLIT = contract can be divided into lots
    competition_mode: Literal["FULL", "SPLIT"] = "FULL"

    total_units: int = Field(default=1, ge=1)
    unit_type: Optional[str] = ""  # e.g. container, shipment, load

    cargo_type: Optional[str] = ""
    vehicle_type: Optional[str] = ""
    required_capacity: Optional[str] = ""

    pickup_location: Optional[Location] = None
    delivery_location: Optional[Location] = None

    pickup_date: Optional[str] = ""
    pickup_time: Optional[str] = ""
    delivery_date: Optional[str] = ""
    delivery_time: Optional[str] = ""

    fragile: Optional[bool] = False
    loading_service: Optional[bool] = False
    unloading_service: Optional[bool] = False

    special_instructions: Optional[str] = ""
    terms: Optional[str] = ""

    # Advisory/target value for the whole contract.
    # This is not a provider bid cap.
    target_total_price: Optional[float] = Field(default=None, ge=0)

    currency: Optional[str] = "OMR"

    bidding_deadline: Optional[str] = ""
    start_date: Optional[str] = ""
    end_date: Optional[str] = ""

    # References to uploaded contract/supporting documents.
    document_ids: List[str] = []

    status: Literal[
        "DRAFT",
        "PUBLISHED",
        "BIDDING",
        "UNDER_REVIEW",
        "AWARDED",
        "IN_PROGRESS",
        "COMPLETED",
        "CANCELLED",
    ] = "DRAFT"


class ContractUpdate(BaseModel):
    """Partial update for a contract before it reaches a locked state."""

    title: Optional[str] = None
    description: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    contract_number: Optional[str] = None

    competition_mode: Optional[Literal["FULL", "SPLIT"]] = None

    total_units: Optional[int] = Field(default=None, ge=1)
    unit_type: Optional[str] = None

    cargo_type: Optional[str] = None
    vehicle_type: Optional[str] = None
    required_capacity: Optional[str] = None

    pickup_location: Optional[Location] = None
    delivery_location: Optional[Location] = None

    pickup_date: Optional[str] = None
    pickup_time: Optional[str] = None
    delivery_date: Optional[str] = None
    delivery_time: Optional[str] = None

    fragile: Optional[bool] = None
    loading_service: Optional[bool] = None
    unloading_service: Optional[bool] = None

    special_instructions: Optional[str] = None
    terms: Optional[str] = None

    target_total_price: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = None

    bidding_deadline: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    document_ids: Optional[List[str]] = None


class ContractLotCreate(BaseModel):
    """A competition lot within a split contract."""

    name: str
    lot_number: Optional[str] = ""
    quantity: int = Field(ge=1)
    unit_type: Optional[str] = ""

    description: Optional[str] = ""
    vehicle_type: Optional[str] = ""
    required_capacity: Optional[str] = ""

    pickup_location: Optional[Location] = None
    delivery_location: Optional[Location] = None

    pickup_date: Optional[str] = ""
    pickup_time: Optional[str] = ""
    delivery_date: Optional[str] = ""
    delivery_time: Optional[str] = ""

    target_price: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = "OMR"

    status: Literal[
        "DRAFT",
        "PUBLISHED",
        "BIDDING",
        "UNDER_REVIEW",
        "AWARDED",
        "IN_PROGRESS",
        "COMPLETED",
        "CANCELLED",
    ] = "DRAFT"


class ContractLotUpdate(BaseModel):
    """Partial update for a contract lot."""

    name: Optional[str] = None
    lot_number: Optional[str] = None
    quantity: Optional[int] = Field(default=None, ge=1)
    unit_type: Optional[str] = None

    description: Optional[str] = None
    vehicle_type: Optional[str] = None
    required_capacity: Optional[str] = None

    pickup_location: Optional[Location] = None
    delivery_location: Optional[Location] = None

    pickup_date: Optional[str] = None
    pickup_time: Optional[str] = None
    delivery_date: Optional[str] = None
    delivery_time: Optional[str] = None

    target_price: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = None


class ContractBidCreate(BaseModel):
    """Provider/company bid against a full contract or a specific lot."""

    # None = compete for the whole contract.
    # Set when bidding against one specific lot.
    lot_id: Optional[str] = None

    quantity_offered: int = Field(ge=1)

    # Authoritative amount will be calculated/stored by the backend.
    unit_price: float = Field(gt=0)

    execution_days: Optional[int] = Field(default=None, ge=1)
    available_vehicles: Optional[int] = Field(default=None, ge=0)

    notes: Optional[str] = ""
    document_ids: List[str] = []

    status: Literal[
        "DRAFT",
        "SUBMITTED",
        "UNDER_REVIEW",
        "SHORTLISTED",
        "AWARDED",
        "REJECTED",
        "WITHDRAWN",
        "EXPIRED",
    ] = "SUBMITTED"


class ContractBidUpdate(BaseModel):
    """Allowed editable fields while a bid is still editable."""

    quantity_offered: Optional[int] = Field(default=None, ge=1)
    unit_price: Optional[float] = Field(default=None, gt=0)

    execution_days: Optional[int] = Field(default=None, ge=1)
    available_vehicles: Optional[int] = Field(default=None, ge=0)

    notes: Optional[str] = None
    document_ids: Optional[List[str]] = None


class ContractAwardCreate(BaseModel):
    """Admin award/allocation decision derived from a submitted bid."""

    bid_id: str
    provider_id: str

    # Supports full or partial award.
    quantity_awarded: int = Field(ge=1)

    # Normally inherited from the accepted bid and revalidated server-side.
    unit_price: Optional[float] = Field(default=None, gt=0)

    notes: Optional[str] = ""

    status: Literal[
        "AWARDED",
        "ACCEPTED",
        "IN_PROGRESS",
        "COMPLETED",
        "CANCELLED",
    ] = "AWARDED"
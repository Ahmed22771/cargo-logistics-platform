"""CARGO Pricing Service.

A self-contained, HTTP/DB-agnostic pricing engine. The FastAPI layer only calls
`PricingService.quote(...)`; nothing here imports FastAPI, Mongo or React. This
keeps the pricing logic portable — it can later be extracted into its own module
(or re-implemented in Go/Node/Java) behind the same data contract without touching
the customer flow or the bid system.

Stage 1 uses a configurable RULE-BASED provider (no market data yet). Prices are
NOT hardcoded per shipment: they derive from a config table (base fare, per-km
rate, per-vehicle multipliers, service surcharges, spread). Later we can register
a HistoricalPricingProvider / MarketPricingProvider implementing the same
`PricingProvider` interface without changing callers.
"""
from __future__ import annotations

import math
from typing import Optional, Protocol


# Version tag stored on every shipment's pricing snapshot so a future algorithm
# change never silently rewrites historical advisory prices.
PRICING_VERSION = "rule_based_v1"
PRICING_CURRENCY = "OMR"

# ---------------------------------------------------------------------------
# Configuration (extensible — could later be loaded from DB/remote config).
# Every vehicle type has its OWN multiplier, so the advisory price differs by
# vehicle type. Keys are the canonical stored vehicle_type values.
# ---------------------------------------------------------------------------
RULE_CONFIG = {
    "base_fare": 15.0,          # flat pickup fee (OMR)
    "per_km": 0.35,             # distance rate (OMR/km)
    "min_distance_km": 5.0,     # floor so a missing/tiny distance still prices sanely
    "spread": 0.20,             # +/- band around the computed base -> min/max
    "fragile_factor": 1.10,     # fragile cargo surcharge (x)
    "loading_surcharge": 5.0,   # flat OMR added when loading service requested
    "unloading_surcharge": 5.0, # flat OMR added when unloading service requested
    "vehicle_multipliers": {
        "car": 0.8,
        "pickup": 1.0,
        "box_truck": 1.3,
        "flatbed": 1.5,
        "dump_truck": 1.6,
        "car_carrier": 1.7,
        "refrigerated": 1.8,
        "container": 1.9,
        "tanker": 2.0,
        "trailer": 2.2,
        "heavy_truck": 2.5,
    },
    "default_vehicle_multiplier": 1.0,
}


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometres."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _coord(loc) -> Optional[tuple]:
    if not loc or not isinstance(loc, dict):
        return None
    lat, lng = loc.get("lat"), loc.get("lng")
    if lat is None or lng is None:
        return None
    try:
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None


class PricingProvider(Protocol):
    """Strategy interface. New pricing strategies implement `quote`."""

    version: str

    def quote(self, inputs: dict) -> dict: ...


class RuleBasedPricingProvider:
    """Deterministic, config-driven pricing. No external calls."""

    version = PRICING_VERSION

    def __init__(self, config: Optional[dict] = None):
        self.config = config or RULE_CONFIG

    def quote(self, inputs: dict) -> dict:
        cfg = self.config
        pickup = _coord(inputs.get("pickup_location"))
        delivery = _coord(inputs.get("delivery_location"))
        if pickup and delivery:
            distance_km = haversine_km(pickup[0], pickup[1], delivery[0], delivery[1])
        else:
            distance_km = 0.0
        eff_distance = max(distance_km, cfg["min_distance_km"])

        vehicle_type = (inputs.get("vehicle_type") or "").strip().lower()
        mult = cfg["vehicle_multipliers"].get(vehicle_type, cfg["default_vehicle_multiplier"])

        base = (cfg["base_fare"] + cfg["per_km"] * eff_distance) * mult
        if inputs.get("fragile"):
            base *= cfg["fragile_factor"]
        if inputs.get("loading_service"):
            base += cfg["loading_surcharge"]
        if inputs.get("unloading_service"):
            base += cfg["unloading_surcharge"]

        spread = cfg["spread"]
        pricing_min = round(base * (1 - spread))
        pricing_max = round(base * (1 + spread))
        if pricing_max <= pricing_min:
            pricing_max = pricing_min + 1
        advisory_price = round((pricing_min + pricing_max) / 2)

        return {
            "vehicle_type": vehicle_type,
            "distance_km": round(distance_km, 1),
            "pricing_min": pricing_min,
            "pricing_max": pricing_max,
            "advisory_price": advisory_price,
            "pricing_currency": PRICING_CURRENCY,
            "pricing_version": self.version,
        }


class PricingService:
    """Facade used by the app. Swap the provider to change strategy."""

    def __init__(self, provider: Optional[PricingProvider] = None):
        self.provider = provider or RuleBasedPricingProvider()

    def quote(self, inputs: dict) -> dict:
        return self.provider.quote(inputs)


# Default singleton the API layer imports.
pricing_service = PricingService()


def clamp_offer(value, pricing_min, pricing_max, default):
    """Clamp a customer max-offer into [pricing_min, pricing_max]; fall back to
    `default` (advisory) when value is missing/invalid."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    lo, hi = float(pricing_min), float(pricing_max)
    return round(min(max(v, lo), hi))

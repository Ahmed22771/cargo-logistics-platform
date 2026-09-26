import os

from motor.motor_asyncio import AsyncIOMotorClient

mongo_url = os.environ["MONGO_URL"]

client = AsyncIOMotorClient(mongo_url)

db = client[os.environ["DB_NAME"]]


async def ensure_indexes():

    # ================= EXISTING CARGO INDEXES =================

    await db.users.create_index("phone")
    await db.users.create_index("email")

    await db.shipments.create_index("customer_id")
    await db.shipments.create_index("status")

    await db.bids.create_index("shipment_id")
    await db.bids.create_index("driver_id")

    await db.trips.create_index("customer_id")
    await db.trips.create_index("driver_id")

    await db.notifications.create_index("user_id")

    # A trip represents one completed service and can receive exactly one review.
    await db.reviews.create_index("trip_id", unique=True)

    await db.vehicles.create_index(
        [("owner_id", 1), ("plate_number", 1)],
        unique=True,
    )
    await db.vehicles.create_index("owner_id")

    await db.users.create_index("company_id")

    # One transport document per trip.
    await db.transport_documents.create_index("trip_id", unique=True)
    await db.transport_documents.create_index("status")

    # ================= CONTRACTS & COMPETITION =================
    # These indexes support the new B2B contract marketplace.
    # They are intentionally non-destructive and do not change existing data.

    # Contract discovery / admin filtering
    await db.contracts.create_index("status")
    await db.contracts.create_index("created_at")

    # Fast lookup by client/customer when a contract is linked
    # to an existing CARGO customer account.
    await db.contracts.create_index("customer_id")

    # Contract number should be searchable and remains non-unique
    # for backward compatibility and future numbering strategies.
    await db.contracts.create_index("contract_number")

    # Lots belonging to a contract
    await db.contract_lots.create_index("contract_id")
    await db.contract_lots.create_index(
        [("contract_id", 1), ("status", 1)]
    )

    # Competition bids
    await db.contract_bids.create_index("contract_id")
    await db.contract_bids.create_index("lot_id")
    await db.contract_bids.create_index("provider_id")
    await db.contract_bids.create_index("status")

    # Common provider competition queries:
    # "my active bids", "my bids on this contract", etc.
    await db.contract_bids.create_index(
        [("provider_id", 1), ("status", 1), ("created_at", -1)]
    )
    await db.contract_bids.create_index(
        [("contract_id", 1), ("lot_id", 1), ("status", 1)]
    )

    # Awards / contract allocation
    await db.contract_awards.create_index("contract_id")
    await db.contract_awards.create_index("lot_id")
    await db.contract_awards.create_index("bid_id")
    await db.contract_awards.create_index("provider_id")
    await db.contract_awards.create_index("status")

    await db.contract_awards.create_index(
        [("provider_id", 1), ("status", 1), ("created_at", -1)]
    )
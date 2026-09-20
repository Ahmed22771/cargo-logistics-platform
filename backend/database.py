import os
from motor.motor_asyncio import AsyncIOMotorClient

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]


async def ensure_indexes():
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
    await db.vehicles.create_index([("owner_id", 1), ("plate_number", 1)], unique=True)
    await db.vehicles.create_index("owner_id")
    await db.users.create_index("company_id")


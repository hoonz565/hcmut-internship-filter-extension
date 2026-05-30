import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

# Ensure sibling imports work correctly regardless of invocation directory
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from config import MONGO_URI, DB_NAME, COLLECTION_NAME

async def main():
    client = AsyncIOMotorClient(MONGO_URI) 
    collection = client[DB_NAME][COLLECTION_NAME]

    total = await collection.count_documents({})
    failed = await collection.count_documents({"industry_tags": "Other"})
    success = total - failed

    print("=== BÁO CÁO DATABASE ===")
    print(f"Tổng số công ty: {total}")
    print(f"✅ Phân tích thành công (Có Tag): {success}")
    print(f"❌ Chưa phân tích được (Tag 'Other'): {failed}")

if __name__ == "__main__":
    asyncio.run(main())
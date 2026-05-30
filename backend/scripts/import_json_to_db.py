import json
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from dotenv import load_dotenv

# Ensure we can find the .env file in the backend root
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_ROOT = os.path.dirname(_SCRIPT_DIR)
load_dotenv(os.path.join(_BACKEND_ROOT, ".env"))

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("Missing MONGO_URI in .env file")

async def import_json():
    # Kết nối MongoDB bằng URI từ env
    client = AsyncIOMotorClient(MONGO_URI)
    collection = client["hcmut_internship"]["classifications"]

    print("📦 Đang đọc file data.json...")
    with open("data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    # data đang là dictionary, key là tên công ty, value là dict chứa tag
    for company_name, details in data.items():
        tags = details.get("industry_tags", ["Other"])
        skills = details.get("key_skills", [])

        # Lệnh upsert: Có thì ghi đè (xóa Other), chưa có thì thêm mới
        await collection.update_one(
            {"company_name": company_name},
            {"$set": {
                "company_name": company_name,
                "industry_tags": tags,
                "key_skills": skills,
                "updated_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        count += 1
    
    print(f"✅ Tuyệt vời! Đã import thành công {count} công ty vào MongoDB!")

if __name__ == "__main__":
    asyncio.run(import_json())
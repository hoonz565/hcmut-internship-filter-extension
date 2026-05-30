import json
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

async def import_json():
    # Kết nối MongoDB (sửa URI nếu ông dùng config khác)
    client = AsyncIOMotorClient("mongodb+srv://nguyenminhhung05062005_db_user:hDlNKLPCjWHvOs5e@extension.whemms6.mongodb.net/?appName=extension")
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
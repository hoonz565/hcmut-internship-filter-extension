import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "hcmut_internship")

async def migrate_tags():
    client = AsyncIOMotorClient(MONGO_URI)
    collection = client[DB_NAME]["classifications"]
    
    # Từ điển quy hoạch tag
    mapping = {
        "AI": "Data & AI",
        "Data": "Data & AI",
        "DevOps": "Cloud / DevOps",
        "Cloud": "Cloud / DevOps",
        "Blockchain": "Web"  # Gom tạm Blockchain vào Web
    }
    
    cursor = collection.find({})
    count = 0
    print("🚀 Bắt đầu quy hoạch lại dữ liệu...")
    
    async for doc in cursor:
        old_tags = doc.get("industry_tags", [])
        new_tags = set()
        modified = False
        
        for tag in old_tags:
            if tag in mapping:
                new_tags.add(mapping[tag])
                modified = True
            else:
                new_tags.add(tag)
        
        if modified:
            await collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"industry_tags": list(new_tags)}}
            )
            count += 1
            print(f"✅ Đã update: {doc.get('company_name')} -> {list(new_tags)}")
            
    print(f"\n🎉 Hoàn tất! Đã chuyển đổi tag thành công cho {count} công ty.")

if __name__ == "__main__":
    asyncio.run(migrate_tags())
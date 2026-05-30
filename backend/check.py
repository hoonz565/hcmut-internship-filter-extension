import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load config y hệt như cách Antigravity đã làm
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "hcmut_internship")

async def main():
    client = AsyncIOMotorClient(MONGO_URI) 
    collection = client[DB_NAME]["classifications"]

    total = await collection.count_documents({})
    failed = await collection.count_documents({"industry_tags": "Other"})
    success = total - failed

    print("=== BÁO CÁO DATABASE ===")
    print(f"Tổng số công ty: {total}")
    print(f"✅ Phân tích thành công (Có Tag): {success}")
    print(f"❌ Chưa phân tích được (Tag 'Other'): {failed}")

    # --- ĐOẠN CODE MỚI THÊM VÀO ---
    if failed > 0:
        print("\n=== DANH SÁCH 29 CÔNG TY 'OTHER' CẦN KHÁM LẠI ===")
        # Lấy danh sách các công ty bị mác Other
        cursor = collection.find({"industry_tags": "Other"})
        
        count = 1
        async for doc in cursor:
            print(f"{count}. {doc.get('company_name')}")
            count += 1

if __name__ == "__main__":
    asyncio.run(main())
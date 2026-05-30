import asyncio
import aiohttp
import os
from motor.motor_asyncio import AsyncIOMotorClient
import re
from dotenv import load_dotenv

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_ROOT = os.path.dirname(_SCRIPT_DIR)
load_dotenv(os.path.join(_BACKEND_ROOT, ".env"))

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("Missing MONGO_URI in .env file")

async def fix_db():
    client = AsyncIOMotorClient(MONGO_URI)
    collection = client['hcmut_internship']['classifications']
    
    API = 'https://internship.cse.hcmut.edu.vn/home/company/all?t=1780072873951&condition='
    async with aiohttp.ClientSession() as session:
        async with session.get(API) as resp:
            data = await resp.json()
            items = data.get('items') or data.get('data') or (data if isinstance(data, list) else [])
            print('Num items:', len(items))
            
            updated = 0
            for item in items:
                c_id = str(item.get('_id', '')).strip()
                c_name = str(item.get('fullname', c_id)).strip()
                clean_name = re.sub(r'\s*\(Gọi tắt là.*?\)', '', c_name)
                
                if c_id and clean_name:
                    res = await collection.update_one(
                        {'company_name': clean_name},
                        {'$set': {'company_id': c_id}}
                    )
                    if res.modified_count:
                        updated += 1
            print(f'Updated {updated} companies with company_id')

if __name__ == '__main__':
    asyncio.run(fix_db())

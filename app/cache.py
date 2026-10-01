import os
import json
import redis
from dotenv import load_dotenv
 
load_dotenv()
 
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
 
 
def get_cached_summary(account_id: int):
    data = redis_client.get(f"summary:{account_id}")
    return json.loads(data) if data else None
 
 
def set_cached_summary(account_id: int, summary: dict, ttl_seconds: int = 60):
    redis_client.set(f"summary:{account_id}", json.dumps(summary), ex=ttl_seconds)
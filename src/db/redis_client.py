from redis import Redis

from src.config import settings


redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def get_cache_client() -> Redis:
    return redis_client
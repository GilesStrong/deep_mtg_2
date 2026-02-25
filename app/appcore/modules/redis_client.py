import redis
from app.app_settings import APP_SETTINGS


def get_redis() -> redis.Redis:
    return redis.Redis.from_url(APP_SETTINGS.REDIS_URL, decode_responses=True)

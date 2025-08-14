import time
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings

# ENV-configurable (defaults if missing)
RATE_LIMIT_REQ = int(getattr(settings, "RATE_LIMIT_REQ", 60))        # requests per window
RATE_LIMIT_WINDOW = int(getattr(settings, "RATE_LIMIT_WINDOW", 60))  # seconds

def _key(ip: str) -> str:
    return f"ratelimit:{ip}"

class RateLimitMiddleware:
    """
    Simple per-IP token bucket using Django cache.
    Works across multiple workers if cache is shared (e.g., Redis).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = request.META.get("REMOTE_ADDR") or "unknown"
        now = int(time.time())

        bucket = cache.get(_key(ip))
        if not bucket:
            # (tokens_left, window_start)
            bucket = [RATE_LIMIT_REQ, now]
        tokens, start = bucket

        # Refill
        elapsed = now - start
        if elapsed >= RATE_LIMIT_WINDOW:
            tokens = RATE_LIMIT_REQ
            start = now

        if tokens <= 0:
            retry = RATE_LIMIT_WINDOW - elapsed if elapsed < RATE_LIMIT_WINDOW else RATE_LIMIT_WINDOW
            return JsonResponse(
                {"error": "Rate limit exceeded. Try later.", "retry_after_seconds": retry},
                status=429
            )

        # spend one token and persist
        tokens -= 1
        cache.set(_key(ip), [tokens, start], timeout=RATE_LIMIT_WINDOW)

        return self.get_response(request)

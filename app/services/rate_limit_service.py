import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status

from app.config import settings

_attempts: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def enforce_rate_limit(request: Request, namespace: str) -> None:
    key = f"{namespace}:{client_ip(request)}"
    now = time.monotonic()
    window = settings.login_rate_limit_window_seconds
    max_attempts = settings.login_rate_limit_attempts

    with _lock:
        timestamps = [timestamp for timestamp in _attempts[key] if now - timestamp < window]
        if len(timestamps) >= max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas tentativas. Aguarde alguns minutos e tente novamente.",
            )
        timestamps.append(now)
        _attempts[key] = timestamps


def clear_rate_limit(request: Request, namespace: str) -> None:
    key = f"{namespace}:{client_ip(request)}"
    with _lock:
        _attempts.pop(key, None)

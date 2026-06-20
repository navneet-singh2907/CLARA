"""Small in-memory rate limiter for public CLARA demo endpoints."""

import time
from dataclasses import dataclass
from threading import Lock

from fastapi import HTTPException, Request, status

from loan_pipeline.config import get_settings


@dataclass(frozen=True)
class RateLimitPolicy:
    bucket: str
    max_requests: int
    window_seconds: int


_REQUEST_LOG: dict[tuple[str, str], list[float]] = {}
_LOCK = Lock()


def enforce_rate_limit(request: Request, bucket: str) -> None:
    """Limit requests by client IP and endpoint bucket.

    This protects hosted demo API credits. It is intentionally lightweight so it
    works on Vercel/serverless without Redis; each warm instance keeps its own
    short window.
    """
    settings = get_settings()
    if _has_demo_bypass(request, settings.demo_api_key):
        return

    policy = _policy_for(bucket)
    client_id = _client_id(request)
    key = (client_id, policy.bucket)
    now = time.time()
    cutoff = now - policy.window_seconds

    with _LOCK:
        recent = [timestamp for timestamp in _REQUEST_LOG.get(key, []) if timestamp >= cutoff]
        if len(recent) >= policy.max_requests:
            retry_after = max(1, int(policy.window_seconds - (now - min(recent))))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "Live demo quota reached. Try again later or use your demo key.",
                    "bucket": policy.bucket,
                    "limit": policy.max_requests,
                    "window_seconds": policy.window_seconds,
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )
        recent.append(now)
        _REQUEST_LOG[key] = recent


def reset_rate_limits() -> None:
    """Clear limiter state for tests."""
    with _LOCK:
        _REQUEST_LOG.clear()


def _policy_for(bucket: str) -> RateLimitPolicy:
    settings = get_settings()
    window = settings.rate_limit_window_seconds
    if bucket == "review":
        return RateLimitPolicy(bucket=bucket, max_requests=settings.rate_limit_review_requests, window_seconds=window)
    if bucket == "upload":
        return RateLimitPolicy(bucket=bucket, max_requests=settings.rate_limit_upload_requests, window_seconds=window)
    return RateLimitPolicy(bucket=bucket, max_requests=settings.rate_limit_expensive_requests, window_seconds=window)


def _client_id(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()
    return request.client.host if request.client else "unknown"


def _has_demo_bypass(request: Request, demo_api_key: str | None) -> bool:
    if not demo_api_key:
        return False
    return request.headers.get("x-clara-demo-key") == demo_api_key

from __future__ import annotations
import hmac, hashlib, os, time
from fastapi import Request, HTTPException

SECRET = (os.getenv("ORCH_WEBHOOK_SECRET") or "dev-secret").encode()
SIG_HEADER = "X-Signature"
TS_HEADER = "X-Timestamp"
ALLOWED_SKEW = int(os.getenv("ORCH_WEBHOOK_SKEW_SECS", "300"))

def _hmac(body: bytes, ts: str) -> str:
    mac = hmac.new(SECRET, f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return f"sha256={mac}"

def sign_body(body: bytes, ts: int | None = None) -> tuple[str, str]:
    ts_str = str(int(ts or time.time()))
    return _hmac(body, ts_str), ts_str

def verify_hmac(request: Request, raw_body: bytes):
    sig = request.headers.get(SIG_HEADER)
    ts = request.headers.get(TS_HEADER)
    if not sig or not ts:
        raise HTTPException(status_code=401, detail="Missing signature or timestamp")
    try:
        ts_int = int(ts)
    except ValueError:
        raise HTTPException(status_code=401, detail="Bad timestamp")
    if abs(int(time.time()) - ts_int) > ALLOWED_SKEW:
        raise HTTPException(status_code=401, detail="Stale or future-dated webhook")
    good = _hmac(raw_body, ts)
    if not hmac.compare_digest(sig, good):
        raise HTTPException(status_code=401, detail="Bad signature")

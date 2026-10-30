"""Guardrails for the public demo: an access code and limits on paid model calls.

A deployed URL would otherwise let anyone spend the API key. Both limits are
in memory, which is enough for a single-instance demo.
"""

import os
import time
from collections import deque

from fastapi import Header, HTTPException, Request

ACCESS_CODE = os.getenv("DEMO_ACCESS_CODE", "").strip()
PER_IP_PER_HOUR = int(os.getenv("MAX_SCREENS_PER_IP_PER_HOUR", "10"))
PER_DAY = int(os.getenv("MAX_SCREENS_PER_DAY", "100"))

_by_ip: dict[str, deque] = {}
_all: deque = deque()


def require_access(x_access_code: str | None = Header(default=None)) -> None:
    if ACCESS_CODE and x_access_code != ACCESS_CODE:
        raise HTTPException(status_code=401, detail="Enter the demo access code to continue.")


def check_screen_budget(request: Request) -> None:
    """Called before every request that runs the models."""
    t = time.time()
    ip = request.client.host if request.client else "unknown"
    window = _by_ip.setdefault(ip, deque())
    while window and t - window[0] > 3600:
        window.popleft()
    while _all and t - _all[0] > 86400:
        _all.popleft()
    if len(window) >= PER_IP_PER_HOUR:
        raise HTTPException(status_code=429, detail="Too many screenings from this address. Try again in an hour.")
    if len(_all) >= PER_DAY:
        raise HTTPException(status_code=429, detail="The demo reached today's screening limit. Try again tomorrow.")
    window.append(t)
    _all.append(t)

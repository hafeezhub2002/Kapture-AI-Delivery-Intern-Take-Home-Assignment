from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .http_api import api
from .database.database import DB
from .services.gemini_service import _get_conn, gemini_available

logger = logging.getLogger("kapture.server")


@asynccontextmanager
async def _lifespan(application: FastAPI):
    """
    Pre-warm everything on startup so the FIRST Vapi webhook call
    has zero cold-start delay.

    Without this:  first request = DB init + TLS handshake + module imports (~3-8 s extra)
    With this:     first request hits a fully warm server (~0 ms overhead)
    """
    # 1. Force DB seed (loads account data into memory)
    _ = list(DB.list_accounts())
    logger.info("[startup] DB seeded — %d accounts ready", len(list(DB.list_accounts())))

    # 2. Pre-establish Gemini HTTPS keep-alive connection (TLS handshake done at boot, not at call time)
    if gemini_available():
        try:
            _get_conn()   # opens socket + TLS now, not on the first call
            logger.info("[startup] Gemini keep-alive connection established")
        except Exception as exc:
            logger.warning("[startup] Gemini pre-connect failed (will retry on first call): %s", exc)
    else:
        logger.info("[startup] GEMINI_API_KEY not set — running in rule-based mode")

    # 3. Force-import any lazy modules (authentication, services) so they're
    #    already in sys.modules when Vapi fires the first webhook
    from .services import authentication, account_service, payment_service  # noqa: F401
    logger.info("[startup] All modules pre-loaded — server is warm and ready")

    yield  # --- server is running ---

    # Shutdown: close the persistent Gemini connection cleanly
    from .services import gemini_service
    if gemini_service._conn is not None:
        try:
            gemini_service._conn.close()
        except Exception:
            pass
    logger.info("[shutdown] Gemini connection closed")


# Attach lifespan to the existing FastAPI app
api.router.lifespan_context = _lifespan
app = api

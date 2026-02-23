import json
import uuid
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app


def send_ga4_event(event_name: str, *, params: dict | None = None, user_id: str | None = None) -> bool:
    measurement_id = current_app.config.get("GA4_MEASUREMENT_ID")
    api_secret = current_app.config.get("GA4_API_SECRET")
    if not measurement_id or not api_secret:
        return False

    safe_event_name = (event_name or "").strip().lower().replace("-", "_")
    if not safe_event_name:
        return False

    event_params = dict(params or {})
    event_params.setdefault("engagement_time_msec", 100)
    event_params.setdefault("environment", current_app.config.get("GA4_ENVIRONMENT", "development"))

    payload = {
        "client_id": user_id or f"server-{uuid.uuid4()}",
        "events": [
            {
                "name": safe_event_name,
                "params": event_params,
            }
        ],
    }

    endpoint = (
        "https://www.google-analytics.com/mp/collect?"
        + urlencode({"measurement_id": measurement_id, "api_secret": api_secret})
    )
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=3):
            return True
    except Exception as exc:  # pragma: no cover - network edge
        current_app.logger.warning("GA4 event send failed: %s", exc)
        return False

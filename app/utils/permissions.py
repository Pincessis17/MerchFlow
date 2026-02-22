# app/utils/permissions.py

from flask import current_app, session
from ..models import FeatureAccess


def has_feature_access(feature_name):
    user = session.get("user")
    if not user:
        return False

    company_id = user.get("company_id")
    email = user.get("email")

    admin_emails = current_app.config.get("PLATFORM_ADMIN_EMAILS") or set()
    if str(email or "").strip().lower() in admin_emails:
        return True

    access = FeatureAccess.query.filter_by(
        company_id=company_id,
        email=email,
        feature=feature_name,
        is_enabled=True
    ).first()

    return access is not None

# app/utils/permissions.py

from flask import session
from ..models import FeatureAccess


def has_feature_access(feature_name):
    user = session.get("user")
    if not user:
        return False

    company_id = user.get("company_id")
    email = user.get("email")
    role = str(user.get("role") or "").strip().lower()

    if role == "admin":
        return True

    access = FeatureAccess.query.filter_by(
        company_id=company_id,
        email=email,
        feature=feature_name,
        is_enabled=True
    ).first()

    return access is not None

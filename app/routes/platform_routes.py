import csv
import io
from datetime import datetime, timedelta

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
    flash,
)
from sqlalchemy import func, text

from .. import db
from ..models import (
    Company,
    Invoice,
    LoginAttempt,
    PlatformAuditLog,
    PlatformNotification,
    Product,
    Sale,
    SubscriptionPlan,
    TenantSubscription,
    User,
)
from ..utils.analytics import send_ga4_event
from ..utils.notifications import create_platform_notification, send_email_notification
from ..utils.platform_security import (
    clear_platform_elevated_session,
    log_platform_audit,
    platform_owner_elevated_required,
    platform_owner_required,
    set_platform_elevated_session,
)

platform_bp = Blueprint("platform", __name__, url_prefix="/platform")


def _latest_subscription(company_id: int):
    return (
        TenantSubscription.query.filter_by(company_id=company_id)
        .order_by(TenantSubscription.created_at.desc())
        .first()
    )


def _monthly_recurring_value(subscription: TenantSubscription) -> float:
    amount = float(subscription.amount or 0)
    if (subscription.billing_cycle or "monthly").lower() == "yearly":
        return amount / 12.0
    return amount


def _safe_float(raw_value, default: float = 0.0) -> float:
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return default


def _safe_int(raw_value, default: int = 0) -> int:
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default


def _platform_owner_emails():
    return set(current_app.config.get("PLATFORM_ADMIN_EMAILS") or set())


def _email_platform_owners(subject: str, body: str):
    for owner_email in _platform_owner_emails():
        send_email_notification(owner_email, subject, body)


@platform_bp.route("/elevate", methods=["GET", "POST"])
@platform_owner_required
def elevate_access():
    next_url = request.args.get("next") or url_for("platform.dashboard")
    user = User.query.get_or_404((session.get("user") or {}).get("id"))

    if request.method == "POST":
        password = request.form.get("password") or ""
        if not user.check_password(password):
            flash("Invalid password for elevated access.", "error")
            return render_template("platform/elevate.html", next_url=next_url)

        set_platform_elevated_session()
        log_platform_audit(
            "platform.elevated_access",
            "session",
            details="Platform owner re-authenticated for elevated dashboard access.",
        )
        db.session.commit()
        return redirect(next_url)

    return render_template("platform/elevate.html", next_url=next_url)


@platform_bp.route("/clear-elevation", methods=["POST"])
@platform_owner_required
def clear_elevation():
    clear_platform_elevated_session()
    flash("Elevated access session cleared.", "info")
    return redirect(url_for("platform.elevate_access"))


@platform_bp.route("/", methods=["GET"])
@platform_owner_elevated_required
def dashboard():
    companies = Company.query.order_by(Company.created_at.desc()).all()
    active_count = sum(1 for c in companies if c.status == "active" and not c.is_suspended)
    trial_count = sum(1 for c in companies if c.status == "trial" and not c.is_suspended)
    cancelled_count = sum(1 for c in companies if c.status == "cancelled")
    suspended_count = sum(1 for c in companies if c.is_suspended)

    active_subscriptions = (
        TenantSubscription.query.filter(TenantSubscription.status == "active")
        .order_by(TenantSubscription.created_at.desc())
        .all()
    )

    mrr = sum(_monthly_recurring_value(sub) for sub in active_subscriptions)
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    cancelled_this_month = (
        TenantSubscription.query.filter(
            TenantSubscription.status == "cancelled",
            TenantSubscription.cancelled_at.isnot(None),
            TenantSubscription.cancelled_at >= month_start,
        ).count()
    )
    denominator = max(len(active_subscriptions) + cancelled_this_month, 1)
    churn_rate_pct = round((cancelled_this_month / denominator) * 100.0, 2)

    plan_breakdown = {}
    for sub in active_subscriptions:
        plan_name = (sub.plan.name if sub.plan else "Unassigned").strip()
        plan_breakdown[plan_name] = plan_breakdown.get(plan_name, 0) + 1

    usage_metrics = []
    for company in companies:
        latest_subscription = _latest_subscription(company.id)
        usage_metrics.append(
            {
                "company": company,
                "subscription": latest_subscription,
                "users": User.query.filter_by(company_id=company.id).count(),
                "products": Product.query.filter_by(company_id=company.id).count(),
                "sales": Sale.query.filter_by(company_id=company.id).count(),
                "invoices": Invoice.query.filter_by(company_id=company.id).count(),
            }
        )

    cutoff_24h = datetime.utcnow() - timedelta(hours=24)
    failed_logins_24h = LoginAttempt.query.filter(
        LoginAttempt.is_success.is_(False),
        LoginAttempt.created_at >= cutoff_24h,
    ).count()
    recent_failed_logins = (
        LoginAttempt.query.filter(LoginAttempt.is_success.is_(False))
        .order_by(LoginAttempt.created_at.desc())
        .limit(30)
        .all()
    )
    abuse_signals = (
        db.session.query(
            LoginAttempt.ip_address.label("ip"),
            func.count(LoginAttempt.id).label("failed_count"),
        )
        .filter(
            LoginAttempt.is_success.is_(False),
            LoginAttempt.created_at >= cutoff_24h,
        )
        .group_by(LoginAttempt.ip_address)
        .having(func.count(LoginAttempt.id) >= 5)
        .order_by(func.count(LoginAttempt.id).desc())
        .all()
    )

    unread_notifications = (
        PlatformNotification.query.filter_by(is_read=False)
        .order_by(PlatformNotification.created_at.desc())
        .limit(20)
        .all()
    )

    recent_audit_logs = (
        PlatformAuditLog.query.order_by(PlatformAuditLog.created_at.desc()).limit(30).all()
    )

    daily_new_subscribers = []
    for day_offset in range(13, -1, -1):
        day = (datetime.utcnow() - timedelta(days=day_offset)).date()
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        count = Company.query.filter(
            Company.created_at >= day_start,
            Company.created_at <= day_end,
        ).count()
        daily_new_subscribers.append({"date": day.strftime("%Y-%m-%d"), "count": count})

    total_subscribers = max(len(companies), 1)
    conversion_rate_pct = round((active_count / total_subscribers) * 100.0, 2)

    monthly_revenue_trends = {}
    for sub in active_subscriptions:
        month_key = sub.created_at.strftime("%Y-%m")
        monthly_revenue_trends[month_key] = monthly_revenue_trends.get(month_key, 0.0) + _monthly_recurring_value(sub)

    app_start_time = current_app.config.get("APP_START_TIME")
    uptime_seconds = 0
    if app_start_time:
        uptime_seconds = int((datetime.utcnow() - app_start_time).total_seconds())

    db_ok = True
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return render_template(
        "platform/dashboard.html",
        title="Platform Dashboard",
        active_count=active_count,
        trial_count=trial_count,
        cancelled_count=cancelled_count,
        suspended_count=suspended_count,
        total_subscribers=len(companies),
        mrr=mrr,
        churn_rate_pct=churn_rate_pct,
        plan_breakdown=plan_breakdown,
        usage_metrics=usage_metrics,
        failed_logins_24h=failed_logins_24h,
        recent_failed_logins=recent_failed_logins,
        abuse_signals=abuse_signals,
        unread_notifications=unread_notifications,
        recent_audit_logs=recent_audit_logs,
        daily_new_subscribers=daily_new_subscribers,
        conversion_rate_pct=conversion_rate_pct,
        monthly_revenue_trends=sorted(monthly_revenue_trends.items(), key=lambda x: x[0]),
        active_tenant_count=active_count,
        db_ok=db_ok,
        uptime_seconds=uptime_seconds,
    )


@platform_bp.route("/notifications/poll", methods=["GET"])
@platform_owner_elevated_required
def poll_notifications():
    since_id = _safe_int(request.args.get("since_id"), default=0)
    notifications = (
        PlatformNotification.query.filter(PlatformNotification.id > since_id)
        .order_by(PlatformNotification.id.asc())
        .limit(50)
        .all()
    )

    payload = [
        {
            "id": n.id,
            "category": n.category,
            "event_type": n.event_type,
            "title": n.title,
            "message": n.message,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]

    return jsonify({"notifications": payload})


@platform_bp.route("/notifications/mark-read", methods=["POST"])
@platform_owner_elevated_required
def mark_notifications_read():
    ids = request.form.getlist("notification_ids")
    if ids:
        PlatformNotification.query.filter(PlatformNotification.id.in_(ids)).update(
            {"is_read": True},
            synchronize_session=False,
        )
        db.session.commit()
    return redirect(url_for("platform.dashboard"))


@platform_bp.route("/plans", methods=["GET", "POST"])
@platform_owner_elevated_required
def plans():
    if request.method == "POST":
        code = (request.form.get("code") or "").strip().lower()
        name = (request.form.get("name") or "").strip()
        monthly_price = _safe_float(request.form.get("monthly_price"), 0.0)
        yearly_price_raw = (request.form.get("yearly_price") or "").strip()
        yearly_price = _safe_float(yearly_price_raw, 0.0) if yearly_price_raw else None
        max_users_raw = (request.form.get("max_users") or "").strip()
        max_users = _safe_int(max_users_raw, 0) if max_users_raw else None

        if not code or not name:
            flash("Plan code and name are required.", "error")
            return redirect(url_for("platform.plans"))

        existing = SubscriptionPlan.query.filter_by(code=code).first()
        if existing:
            flash("Plan code already exists.", "error")
            return redirect(url_for("platform.plans"))

        plan = SubscriptionPlan(
            code=code,
            name=name,
            monthly_price=max(monthly_price, 0.0),
            yearly_price=yearly_price,
            max_users=max_users if max_users and max_users > 0 else None,
            is_active=True,
        )
        db.session.add(plan)
        log_platform_audit("subscription_plan.created", "subscription_plan", details=f"Plan code={code}")
        db.session.commit()
        flash("Subscription plan created.", "success")
        return redirect(url_for("platform.plans"))

    plans_list = SubscriptionPlan.query.order_by(SubscriptionPlan.created_at.desc()).all()
    return render_template("platform/plans.html", title="Subscription Plans", plans=plans_list)


@platform_bp.route("/plans/<int:plan_id>/toggle", methods=["POST"])
@platform_owner_elevated_required
def toggle_plan(plan_id):
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    plan.is_active = not bool(plan.is_active)
    log_platform_audit(
        "subscription_plan.toggled",
        "subscription_plan",
        target_id=str(plan.id),
        details=f"is_active={plan.is_active}",
    )
    db.session.commit()
    flash("Plan status updated.", "success")
    return redirect(url_for("platform.plans"))


@platform_bp.route("/tenants", methods=["GET"])
@platform_owner_elevated_required
def tenants():
    companies = Company.query.order_by(Company.created_at.desc()).all()
    plans = SubscriptionPlan.query.filter_by(is_active=True).order_by(SubscriptionPlan.name.asc()).all()
    tenant_rows = []
    for company in companies:
        tenant_rows.append({"company": company, "subscription": _latest_subscription(company.id)})

    return render_template(
        "platform/tenants.html",
        title="Tenants",
        tenant_rows=tenant_rows,
        plans=plans,
    )


@platform_bp.route("/tenants/create", methods=["POST"])
@platform_owner_elevated_required
def create_tenant():
    company_name = (request.form.get("company_name") or "").strip()
    company_email = (request.form.get("company_email") or "").strip().lower() or None
    admin_name = (request.form.get("admin_name") or "").strip() or "Admin"
    admin_email = (request.form.get("admin_email") or "").strip().lower()
    admin_password = request.form.get("admin_password") or ""
    plan_id = _safe_int(request.form.get("plan_id"), 0) or None
    status = (request.form.get("status") or "trial").strip().lower()
    billing_cycle = (request.form.get("billing_cycle") or "monthly").strip().lower()
    amount = max(_safe_float(request.form.get("amount"), 0.0), 0.0)

    if not company_name or not admin_email or not admin_password:
        flash("Company name, admin email, and admin password are required.", "error")
        return redirect(url_for("platform.tenants"))

    existing_admin_user = User.query.filter_by(email=admin_email).first()
    if existing_admin_user:
        flash("Admin email already exists.", "error")
        return redirect(url_for("platform.tenants"))

    company = Company(
        name=company_name,
        email=company_email,
        status=status if status in {"trial", "active", "cancelled"} else "trial",
        trial_ends_at=datetime.utcnow() + timedelta(days=14),
    )
    db.session.add(company)
    db.session.flush()

    admin_user = User(
        company_id=company.id,
        email=admin_email,
        name=admin_name,
        role="admin",
    )
    admin_user.set_password(admin_password)
    db.session.add(admin_user)

    subscription = TenantSubscription(
        company_id=company.id,
        plan_id=plan_id,
        status=company.status,
        billing_cycle=billing_cycle if billing_cycle in {"monthly", "yearly"} else "monthly",
        amount=amount,
        started_at=datetime.utcnow(),
        trial_ends_at=company.trial_ends_at if company.status == "trial" else None,
        current_period_end=datetime.utcnow() + timedelta(days=30),
    )
    db.session.add(subscription)

    create_platform_notification(
        event_type="tenant.registered",
        category="success",
        title="New tenant subscribed",
        message=f"{company.name} has been created with status '{company.status}'.",
        company_id=company.id,
        payload={"company_id": company.id, "company_name": company.name},
    )
    log_platform_audit(
        "tenant.created",
        "company",
        target_id=str(company.id),
        company_id=company.id,
        details=f"status={company.status}",
    )
    send_ga4_event(
        "tenant_registered",
        params={
            "company_id": company.id,
            "status": company.status,
            "plan_id": plan_id or 0,
            "billing_cycle": subscription.billing_cycle,
        },
    )
    _email_platform_owners(
        "New tenant subscription",
        (
            f"New tenant created: {company.name} (ID {company.id})\n"
            f"Status: {company.status}\n"
            f"Admin: {admin_email}"
        ),
    )
    if company_email:
        send_email_notification(
            company_email,
            "Welcome to MerchFlow",
            (
                f"Your tenant '{company.name}' has been created.\n"
                f"Admin login email: {admin_email}\n"
                "Please sign in and update your profile settings."
            ),
        )

    db.session.commit()
    flash("Tenant company created successfully.", "success")
    return redirect(url_for("platform.tenants"))


@platform_bp.route("/tenants/<int:company_id>/suspend", methods=["POST"])
@platform_owner_elevated_required
def suspend_tenant(company_id):
    company = Company.query.get_or_404(company_id)
    company.is_suspended = True
    company.suspended_at = datetime.utcnow()
    company.status = "cancelled" if company.status == "cancelled" else "active"

    create_platform_notification(
        event_type="tenant.suspended",
        category="warning",
        title="Tenant suspended",
        message=f"{company.name} has been suspended by platform owner.",
        company_id=company.id,
    )
    log_platform_audit(
        "tenant.suspended",
        "company",
        target_id=str(company.id),
        company_id=company.id,
    )
    db.session.commit()
    flash("Tenant suspended.", "info")
    return redirect(url_for("platform.tenants"))


@platform_bp.route("/tenants/<int:company_id>/activate", methods=["POST"])
@platform_owner_elevated_required
def activate_tenant(company_id):
    company = Company.query.get_or_404(company_id)
    company.is_suspended = False
    company.suspended_at = None
    if company.status == "cancelled":
        company.status = "active"

    create_platform_notification(
        event_type="tenant.activated",
        category="success",
        title="Tenant reactivated",
        message=f"{company.name} has been reactivated.",
        company_id=company.id,
    )
    log_platform_audit(
        "tenant.activated",
        "company",
        target_id=str(company.id),
        company_id=company.id,
    )
    db.session.commit()
    flash("Tenant activated.", "success")
    return redirect(url_for("platform.tenants"))


@platform_bp.route("/tenants/<int:company_id>/cancel", methods=["POST"])
@platform_owner_elevated_required
def cancel_tenant(company_id):
    company = Company.query.get_or_404(company_id)
    company.status = "cancelled"
    latest_subscription = _latest_subscription(company.id)
    if latest_subscription:
        latest_subscription.status = "cancelled"
        latest_subscription.cancelled_at = datetime.utcnow()

    create_platform_notification(
        event_type="tenant.cancelled",
        category="warning",
        title="Tenant cancelled",
        message=f"{company.name} has been cancelled.",
        company_id=company.id,
    )
    log_platform_audit(
        "tenant.cancelled",
        "company",
        target_id=str(company.id),
        company_id=company.id,
    )
    send_ga4_event(
        "tenant_cancelled",
        params={"company_id": company.id, "company_name": company.name},
    )
    _email_platform_owners(
        "Tenant cancellation",
        f"Tenant {company.name} (ID {company.id}) was cancelled.",
    )
    if company.email:
        send_email_notification(
            company.email,
            "Subscription cancelled",
            f"Your tenant subscription for {company.name} has been cancelled.",
        )
    db.session.commit()
    flash("Tenant cancelled.", "info")
    return redirect(url_for("platform.tenants"))


@platform_bp.route("/subscriptions/<int:subscription_id>/change", methods=["POST"])
@platform_owner_elevated_required
def change_subscription(subscription_id):
    subscription = TenantSubscription.query.get_or_404(subscription_id)
    old_plan_id = subscription.plan_id
    old_status = subscription.status

    plan_id = _safe_int(request.form.get("plan_id"), 0) or None
    status = (request.form.get("status") or subscription.status).strip().lower()
    billing_cycle = (request.form.get("billing_cycle") or subscription.billing_cycle).strip().lower()
    amount = max(_safe_float(request.form.get("amount"), subscription.amount), 0.0)

    subscription.plan_id = plan_id
    subscription.status = status if status in {"trial", "active", "cancelled"} else subscription.status
    subscription.billing_cycle = billing_cycle if billing_cycle in {"monthly", "yearly"} else subscription.billing_cycle
    subscription.amount = amount
    subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
    if subscription.status == "cancelled":
        subscription.cancelled_at = datetime.utcnow()
    else:
        subscription.cancelled_at = None

    company = Company.query.get(subscription.company_id)
    if company:
        company.status = subscription.status

    create_platform_notification(
        event_type="subscription.updated",
        category="info",
        title="Subscription updated",
        message=f"Subscription for tenant ID {subscription.company_id} was updated.",
        company_id=subscription.company_id,
        payload={
            "subscription_id": subscription.id,
            "old_plan_id": old_plan_id,
            "new_plan_id": plan_id,
            "old_status": old_status,
            "new_status": subscription.status,
        },
    )
    log_platform_audit(
        "subscription.updated",
        "tenant_subscription",
        target_id=str(subscription.id),
        company_id=subscription.company_id,
        details=f"status={subscription.status}, plan_id={plan_id}",
    )
    send_ga4_event(
        "subscription_changed",
        params={
            "subscription_id": subscription.id,
            "company_id": subscription.company_id,
            "status": subscription.status,
            "billing_cycle": subscription.billing_cycle,
            "plan_id": subscription.plan_id or 0,
        },
    )
    _email_platform_owners(
        "Subscription updated",
        (
            f"Tenant ID {subscription.company_id} subscription changed.\n"
            f"Status: {subscription.status}\n"
            f"Billing cycle: {subscription.billing_cycle}\n"
            f"Amount: {subscription.amount:.2f}"
        ),
    )
    db.session.commit()
    flash("Subscription updated.", "success")
    return redirect(url_for("platform.tenants"))


@platform_bp.route("/subscriptions/<int:subscription_id>/payment-failed", methods=["POST"])
@platform_owner_elevated_required
def mark_subscription_payment_failed(subscription_id):
    subscription = TenantSubscription.query.get_or_404(subscription_id)
    reason = (request.form.get("reason") or "Payment failure").strip()
    company = Company.query.get(subscription.company_id)

    create_platform_notification(
        event_type="subscription.payment_failed",
        category="warning",
        title="Subscription payment failed",
        message=f"Payment failed for tenant ID {subscription.company_id}.",
        company_id=subscription.company_id,
        payload={"reason": reason, "subscription_id": subscription.id},
    )
    log_platform_audit(
        "subscription.payment_failed",
        "tenant_subscription",
        target_id=str(subscription.id),
        company_id=subscription.company_id,
        details=reason,
    )
    send_ga4_event(
        "subscription_payment_failed",
        params={
            "subscription_id": subscription.id,
            "company_id": subscription.company_id,
            "reason": reason,
        },
    )
    _email_platform_owners(
        "Subscription payment failure",
        (
            f"Subscription ID {subscription.id} payment failed.\n"
            f"Tenant: {company.name if company else subscription.company_id}\n"
            f"Reason: {reason}"
        ),
    )
    db.session.commit()
    flash("Payment failure logged and notifications sent.", "info")
    return redirect(url_for("platform.tenants"))


@platform_bp.route("/subscriptions/send-renewal-reminders", methods=["POST"])
@platform_owner_elevated_required
def send_renewal_reminders():
    now = datetime.utcnow()
    window_end = now + timedelta(days=7)
    subscriptions = (
        TenantSubscription.query.filter(
            TenantSubscription.status == "active",
            TenantSubscription.current_period_end.isnot(None),
            TenantSubscription.current_period_end >= now,
            TenantSubscription.current_period_end <= window_end,
        )
        .order_by(TenantSubscription.current_period_end.asc())
        .all()
    )

    reminder_count = 0
    for subscription in subscriptions:
        company = Company.query.get(subscription.company_id)
        if not company:
            continue
        due_date = subscription.current_period_end.strftime("%Y-%m-%d")
        create_tenant_notification(
            company_id=company.id,
            event_type="subscription.renewal_reminder",
            title="Subscription renewal reminder",
            message=f"Your subscription renews on {due_date}.",
            category="info",
            payload={"subscription_id": subscription.id, "due_date": due_date},
        )
        if company.email:
            send_email_notification(
                company.email,
                "Subscription renewal reminder",
                f"Your subscription is due for renewal on {due_date}.",
            )
        reminder_count += 1

    log_platform_audit(
        "subscription.renewal_reminders_sent",
        "tenant_subscription",
        details=f"count={reminder_count}",
    )
    db.session.commit()
    flash(f"Sent {reminder_count} renewal reminders.", "success")
    return redirect(url_for("platform.tenants"))


@platform_bp.route("/audit-logs", methods=["GET"])
@platform_owner_elevated_required
def audit_logs():
    logs = PlatformAuditLog.query.order_by(PlatformAuditLog.created_at.desc()).limit(300).all()
    return render_template("platform/audit_logs.html", title="Platform Audit Logs", logs=logs)


@platform_bp.route("/reports/subscribers.csv", methods=["GET"])
@platform_owner_elevated_required
def export_subscribers_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "company_id",
            "company_name",
            "company_email",
            "status",
            "is_suspended",
            "created_at",
            "subscription_status",
            "billing_cycle",
            "amount",
            "plan",
            "users_count",
        ]
    )

    companies = Company.query.order_by(Company.created_at.asc()).all()
    for company in companies:
        latest = _latest_subscription(company.id)
        users_count = User.query.filter_by(company_id=company.id).count()
        writer.writerow(
            [
                company.id,
                company.name,
                company.email or "",
                company.status,
                "yes" if company.is_suspended else "no",
                company.created_at.isoformat(),
                latest.status if latest else "",
                latest.billing_cycle if latest else "",
                f"{float(latest.amount):.2f}" if latest else "",
                latest.plan.name if latest and latest.plan else "",
                users_count,
            ]
        )

    content = output.getvalue()
    output.close()
    filename = f"platform_subscribers_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@platform_bp.route("/health", methods=["GET"])
@platform_owner_elevated_required
def platform_health():
    app_start_time = current_app.config.get("APP_START_TIME")
    uptime_seconds = 0
    if app_start_time:
        uptime_seconds = int((datetime.utcnow() - app_start_time).total_seconds())

    db_ok = True
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {
        "db_ok": db_ok,
        "uptime_seconds": uptime_seconds,
        "timestamp": datetime.utcnow().isoformat(),
    }

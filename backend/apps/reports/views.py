from decimal import Decimal
from datetime import timedelta

from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.db.models.functions import TruncDay, TruncWeek
from django.utils.dateparse import parse_date
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.expenses.models import Expense
from apps.invoices.models import Invoice
from apps.inventory.models import Product
from apps.sales.models import Sale


class ReportSummaryView(APIView):
    def get(self, request):
        business_id = request.query_params.get("business")
        period = request.query_params.get("period", "all")
        start_date = parse_date(request.query_params.get("start_date", ""))
        end_date = parse_date(request.query_params.get("end_date", ""))

        sales = Sale.objects.all()
        invoices = Invoice.objects.all()
        expenses = Expense.objects.all()
        products = Product.objects.all()

        if business_id:
            sales = sales.filter(business_id=business_id)
            invoices = invoices.filter(sale__business_id=business_id)
            expenses = expenses.filter(business_id=business_id)
            products = products.filter(business_id=business_id)

        if period == "daily":
            today = timezone.localdate()
            sales = sales.filter(created_at__date=today)
            expenses = expenses.filter(created_at__date=today)
            invoices = invoices.filter(created_at__date=today)
        elif period == "weekly":
            week_start = timezone.localdate() - timedelta(days=6)
            sales = sales.filter(created_at__date__gte=week_start)
            expenses = expenses.filter(created_at__date__gte=week_start)
            invoices = invoices.filter(created_at__date__gte=week_start)

        if start_date:
            sales = sales.filter(created_at__date__gte=start_date)
            expenses = expenses.filter(created_at__date__gte=start_date)
            invoices = invoices.filter(created_at__date__gte=start_date)
        if end_date:
            sales = sales.filter(created_at__date__lte=end_date)
            expenses = expenses.filter(created_at__date__lte=end_date)
            invoices = invoices.filter(created_at__date__lte=end_date)

        revenue = sales.aggregate(
            total=Coalesce(
                Sum("total"),
                Decimal("0.00"),
                output_field=models.DecimalField(max_digits=12, decimal_places=2),
            )
        )["total"]
        expenses_total = expenses.aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0.00"),
                output_field=models.DecimalField(max_digits=12, decimal_places=2),
            )
        )["total"]
        paid_invoices = invoices.filter(status=Invoice.STATUS_PAID).count()
        low_stock = products.filter(stock_quantity__lte=models.F("reorder_level")).count()
        sales_trend_bucket = TruncDay("created_at") if period != "weekly" else TruncWeek("created_at")
        sales_trend = (
            sales.annotate(bucket=sales_trend_bucket)
            .values("bucket")
            .annotate(
                total=Coalesce(
                    Sum("total"),
                    Decimal("0.00"),
                    output_field=models.DecimalField(max_digits=12, decimal_places=2),
                )
            )
            .order_by("bucket")
        )

        return Response(
            {
                "revenue": revenue,
                "expenses": expenses_total,
                "profit": revenue - expenses_total,
                "sales_count": sales.count(),
                "invoice_count": invoices.count(),
                "paid_invoice_count": paid_invoices,
                "low_stock_count": low_stock,
                "period": period,
                "sales_trend": [
                    {
                        "date": row["bucket"].date().isoformat() if row["bucket"] else None,
                        "total": row["total"],
                    }
                    for row in sales_trend
                ],
            }
        )

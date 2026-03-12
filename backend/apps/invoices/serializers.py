from rest_framework import serializers

from .models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    business_id = serializers.IntegerField(source="sale.business_id", read_only=True)
    total = serializers.DecimalField(source="sale.total", max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = ["id", "sale", "invoice_number", "amount_paid", "status", "created_at", "business_id", "total"]

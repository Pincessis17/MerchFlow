from decimal import Decimal

from rest_framework import serializers

from .models import Sale, SaleItem


class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = ["id", "product", "quantity", "unit_price", "line_total"]


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)

    class Meta:
        model = Sale
        fields = ["id", "customer", "business", "subtotal", "tax", "total", "created_at", "items"]
        read_only_fields = ["subtotal", "tax", "total", "created_at"]

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        subtotal = Decimal("0")
        for item in items_data:
            subtotal += Decimal(item["line_total"])
        tax = subtotal * Decimal("0.15")
        total = subtotal + tax
        sale = Sale.objects.create(subtotal=subtotal, tax=tax, total=total, **validated_data)
        SaleItem.objects.bulk_create([SaleItem(sale=sale, **item) for item in items_data])
        return sale

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if items_data is not None:
            instance.items.all().delete()
            subtotal = Decimal("0")
            for item in items_data:
                subtotal += Decimal(item["line_total"])
            instance.subtotal = subtotal
            instance.tax = subtotal * Decimal("0.15")
            instance.total = instance.subtotal + instance.tax
            SaleItem.objects.bulk_create([SaleItem(sale=instance, **item) for item in items_data])
        instance.save()
        return instance

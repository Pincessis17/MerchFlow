from django.db import models
from django.utils import timezone


class Sale(models.Model):
    customer = models.ForeignKey("inventory.Customer", on_delete=models.SET_NULL, null=True, related_name="sales")
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE, related_name="sales")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    def __str__(self):
        return f"Sale #{self.id}"


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("inventory.Product", on_delete=models.SET_NULL, null=True, related_name="sale_items")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

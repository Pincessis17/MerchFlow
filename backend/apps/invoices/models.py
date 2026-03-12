from django.db import models
from django.utils import timezone


class Invoice(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
    ]

    sale = models.ForeignKey("sales.Sale", on_delete=models.CASCADE, related_name="invoices")
    invoice_number = models.CharField(max_length=50)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["sale", "invoice_number"], name="unique_invoice_number_per_sale"),
        ]

    @property
    def business_id(self):
        return self.sale.business_id

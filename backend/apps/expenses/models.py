from django.db import models
from django.utils import timezone


class Expense(models.Model):
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE, related_name="expenses")
    category = models.CharField(max_length=80)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    def __str__(self):
        return f"{self.category} - {self.amount}"

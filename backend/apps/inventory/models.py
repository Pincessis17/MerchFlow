from django.db import models


class Product(models.Model):
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=120)
    sku = models.CharField(max_length=80)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_quantity = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "sku"], name="unique_sku_per_business"),
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.sku} - {self.name}"


class Customer(models.Model):
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE, related_name="customers")
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=60, blank=True)

    def __str__(self):
        return self.name

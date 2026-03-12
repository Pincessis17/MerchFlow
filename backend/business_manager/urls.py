from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.businesses.views import BusinessViewSet
from apps.expenses.views import ExpenseViewSet
from apps.inventory.views import CustomerViewSet, ProductViewSet
from apps.invoices.views import InvoiceViewSet
from apps.sales.views import SaleViewSet
from apps.users.views import UserViewSet

router = DefaultRouter()
router.register("businesses", BusinessViewSet, basename="business")
router.register("users", UserViewSet, basename="user")
router.register("products", ProductViewSet, basename="product")
router.register("customers", CustomerViewSet, basename="customer")
router.register("sales", SaleViewSet, basename="sale")
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("expenses", ExpenseViewSet, basename="expense")


def health(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/reports/", include("apps.reports.urls")),
    path("api/", include(router.urls)),
]

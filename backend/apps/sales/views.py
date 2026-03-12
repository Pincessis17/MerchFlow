from rest_framework import viewsets

from .models import Sale
from .serializers import SaleSerializer


class SaleViewSet(viewsets.ModelViewSet):
    serializer_class = SaleSerializer
    queryset = Sale.objects.select_related("business", "customer").prefetch_related("items").all()

    def get_queryset(self):
        queryset = super().get_queryset()
        business_id = self.request.query_params.get("business")
        if business_id:
            queryset = queryset.filter(business_id=business_id)
        return queryset

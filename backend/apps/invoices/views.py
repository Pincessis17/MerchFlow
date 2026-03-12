from rest_framework import viewsets

from .models import Invoice
from .serializers import InvoiceSerializer


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.select_related("sale", "sale__business").all()

    def get_queryset(self):
        queryset = super().get_queryset()
        business_id = self.request.query_params.get("business")
        if business_id:
            queryset = queryset.filter(sale__business_id=business_id)
        return queryset

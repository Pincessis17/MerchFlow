from rest_framework import viewsets

from .models import Customer, Product
from .serializers import CustomerSerializer, ProductSerializer


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.select_related("business").all()

    def get_queryset(self):
        queryset = super().get_queryset()
        business_id = self.request.query_params.get("business")
        if business_id:
            queryset = queryset.filter(business_id=business_id)
        return queryset


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    queryset = Customer.objects.select_related("business").all()

    def get_queryset(self):
        queryset = super().get_queryset()
        business_id = self.request.query_params.get("business")
        if business_id:
            queryset = queryset.filter(business_id=business_id)
        return queryset

from rest_framework import viewsets

from .models import Expense
from .serializers import ExpenseSerializer


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    queryset = Expense.objects.select_related("business").all()

    def get_queryset(self):
        queryset = super().get_queryset()
        business_id = self.request.query_params.get("business")
        if business_id:
            queryset = queryset.filter(business_id=business_id)
        return queryset

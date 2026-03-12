from rest_framework import viewsets

from .models import User
from .serializers import UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("business").all()
    serializer_class = UserSerializer

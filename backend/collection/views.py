from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAdminUser

from .models import CollectionRun
from .serializers import CollectionRunSerializer


class CollectionRunViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):

    queryset = CollectionRun.objects.all().order_by("-started_at")

    serializer_class = CollectionRunSerializer

    permission_classes = [IsAdminUser]

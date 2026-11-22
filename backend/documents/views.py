
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAdminUser

from .models import SourceDocument
from .serializers import SourceDocumentSerializer


class SourceDocumentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):

    queryset = SourceDocument.objects.select_related(
        "source"
    ).all().order_by("-created_at")

    serializer_class = SourceDocumentSerializer

    permission_classes = [IsAdminUser]



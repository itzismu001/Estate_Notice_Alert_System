from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAdminUser

from .models import (
    SourceDocument,
    DocumentPage,
    ProcessingJob,
)

from .serializers import (
    SourceDocumentSerializer,
    DocumentPageSerializer,
    ProcessingJobSerializer,
)


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


class DocumentPageViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = DocumentPage.objects.select_related(
        "document"
    ).all().order_by("document", "page_number")

    serializer_class = DocumentPageSerializer

    permission_classes = [IsAdminUser]


class ProcessingJobViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = ProcessingJob.objects.select_related(
        "document",
        "page"
    ).all().order_by("-created_at")

    serializer_class = ProcessingJobSerializer

    permission_classes = [IsAdminUser]

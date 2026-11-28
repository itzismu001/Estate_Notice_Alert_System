from django.utils import timezone

from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .models import CollectionRun
from .serializers import (
    CollectionRunSerializer,
    CollectionRunCreateSerializer,
)
from .tasks import execute_collection_run_task


class CollectionRunViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):

    queryset = CollectionRun.objects.all().order_by("-started_at")

    serializer_class = CollectionRunSerializer

    permission_classes = [IsAdminUser]

    def get_serializer_class(self):

        if self.action == "create":
            return CollectionRunCreateSerializer

        return CollectionRunSerializer

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pdf_list = serializer.validated_data["pdf_list"]

        collection_run = CollectionRun.objects.create()

        task_pdf_list = []

        for pdf in pdf_list:
            task_pdf_list.append({
                "source_id": pdf["source_id"],
                "pdf_url": pdf["pdf_url"],
                "title": pdf["title"],
                "publication_date": (
                    pdf["publication_date"].isoformat()
                    if pdf.get("publication_date")
                    else None
                ),
            })

        try:
            execute_collection_run_task.delay(
                collection_run.id,
                task_pdf_list
            )

        except Exception as error:

            collection_run.status = CollectionRun.Status.FAILED
            collection_run.finished_at = timezone.now()
            collection_run.error_message = (
                f"Could not queue collection task: {error}"
            )

            collection_run.save(
                update_fields=[
                    "status",
                    "finished_at",
                    "error_message",
                ]
            )

            return Response(
                CollectionRunSerializer(collection_run).data,
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        return Response(
            CollectionRunSerializer(collection_run).data,
            status=status.HTTP_202_ACCEPTED
        )

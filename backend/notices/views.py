
from django.utils import timezone
from django.db import transaction

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .models import Notice, ReviewHistory
from .serializers import NoticeSerializer


class NoticeViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Notice.objects.prefetch_related(
        "entities",
        "review_history",
        "notice_pages",
    ).select_related(
        "reviewed_by"
    ).all().order_by("-created_at")

    serializer_class = NoticeSerializer

    permission_classes = [IsAdminUser]

    @transaction.atomic
    def update_notice_status(self, request, notice, new_status, action_type):

        if notice.status != Notice.Status.NEEDS_REVIEW:
            return Response(
                {
                    "error": "Only notices awaiting review can be reviewed.",
                    "current_status": notice.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        comments = request.data.get("comments", "")

        previous_status = notice.status

        notice.status = new_status
        notice.reviewed_by = request.user
        notice.reviewed_at = timezone.now()

        notice.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "updated_at",
            ]
        )

        ReviewHistory.objects.create(
            notice=notice,
            reviewed_by=request.user,
            action=action_type,
            previous_status=previous_status,
            new_status=new_status,
            comments=comments,
        )

        return Response(
            {
                "message": f"Notice successfully {new_status.lower()}.",
                "notice_id": notice.id,
                "status": notice.status,
                "reviewed_by": request.user.username,
                "reviewed_at": notice.reviewed_at,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):

        notice = self.get_object()

        return self.update_notice_status(
            request,
            notice,
            Notice.Status.APPROVED,
            ReviewHistory.Action.APPROVED,
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):

        notice = self.get_object()

        return self.update_notice_status(
            request,
            notice,
            Notice.Status.REJECTED,
            ReviewHistory.Action.REJECTED,
        )

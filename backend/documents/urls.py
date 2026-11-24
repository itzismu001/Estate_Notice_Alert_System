from rest_framework.routers import DefaultRouter

from .views import (
    SourceDocumentViewSet,
    DocumentPageViewSet,
    ProcessingJobViewSet,
)


router = DefaultRouter()

router.register(
    "documents",
    SourceDocumentViewSet,
    basename="documents"
)

router.register(
    "document-pages",
    DocumentPageViewSet,
    basename="document-pages"
)

router.register(
    "processing-jobs",
    ProcessingJobViewSet,
    basename="processing-jobs"
)


urlpatterns = router.urls

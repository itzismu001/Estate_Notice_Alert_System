from rest_framework.routers import DefaultRouter

from .views import SourceDocumentViewSet


router = DefaultRouter()

router.register(
    "documents",
    SourceDocumentViewSet,
    basename="documents"
)

urlpatterns = router.urls

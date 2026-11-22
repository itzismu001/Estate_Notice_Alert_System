
from rest_framework.routers import DefaultRouter

from .views import CollectionRunViewSet


router = DefaultRouter()

router.register(
    "collection-runs",
    CollectionRunViewSet,
    basename="collection-run"
)

urlpatterns = router.urls

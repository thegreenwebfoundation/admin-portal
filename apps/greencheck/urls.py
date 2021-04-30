from django.urls import path

from .views import GreencheckStatsView

urlpatterns = [
    path("", GreencheckStatsView.as_view(), name="greencheck-stats-index"),
]

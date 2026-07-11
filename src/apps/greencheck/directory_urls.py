from django.urls import path
from django.views.decorators.cache import cache_page
from django.conf import settings
from .views import DirectoryView

urlpatterns = [
    path("", cache_page(settings.DIRECTORY_CACHE_TIMEOUT)(DirectoryView.as_view()), name="directory-index"),
]

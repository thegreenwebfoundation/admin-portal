from django.urls import path

from .views import DirectoryView

urlpatterns = [
    path("", DirectoryView.as_view(), name="directory-index"),
]

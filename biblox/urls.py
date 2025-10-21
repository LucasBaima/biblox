from django.contrib import admin
from django.urls import path, include
from livros.views import homepage  # homepage em "/"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("livros/", include("livros.urls")),
    path("", homepage, name="homepage"),  # página inicial
]

"""
URL configuration for crime_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    # Custom admin panel (NOT Django's built-in admin)
    path("admin/", include("crime_map.admin_urls", namespace="admin_panel")),
    # Visitor-facing app
    path("", include("crime_map.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

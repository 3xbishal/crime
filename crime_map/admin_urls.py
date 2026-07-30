"""URL configuration for the custom admin panel."""

from django.urls import path

from . import admin_views

app_name = "admin_panel"

urlpatterns = [
    path("login/", admin_views.admin_login, name="login"),
    path("logout/", admin_views.admin_logout, name="logout"),
    path("dashboard/", admin_views.admin_dashboard, name="dashboard"),
    path("upload/", admin_views.admin_upload_csv, name="upload_csv"),
    path("data/", admin_views.admin_data_list, name="data_list"),
    path("data/<int:pk>/", admin_views.admin_data_detail, name="data_detail"),
    path("data/<int:pk>/edit/", admin_views.admin_data_edit, name="data_edit"),
    path("data/<int:pk>/delete/", admin_views.admin_data_delete, name="data_delete"),
    path("data/export/", admin_views.admin_data_export, name="data_export"),
    path("data/export/pdf/", admin_views.admin_data_export_pdf, name="data_export_pdf"),
    path("uploads/", admin_views.admin_upload_list, name="upload_list"),
]

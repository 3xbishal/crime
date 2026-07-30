from django.urls import path

from . import views

app_name = "crime_map"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("map/", views.crime_map_view, name="map"),
    path("api/points/", views.crime_data_api, name="api_points"),
    path("predict/", views.predict_view, name="predict"),
    path("api/predict/", views.predict_api, name="api_predict"),
    path("data/", views.public_data_list, name="public_data_list"),
    path("data/export/", views.public_data_export, name="public_data_export"),
    path("data/export/pdf/", views.public_data_export_pdf, name="public_data_export_pdf"),
]

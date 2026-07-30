from django.urls import path

from . import views

app_name = "crime_map"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("upload/", views.upload_csv, name="upload_csv"),
    path("map/", views.crime_map_view, name="map"),
    path("api/points/", views.crime_data_api, name="api_points"),
    path("predict/", views.predict_view, name="predict"),
    path("api/predict/", views.predict_api, name="api_predict"),
]

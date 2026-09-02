from django.urls import path
from . import views
urlpatterns=[
 path("", views.map_home, name="map_home"),
 path("route/", views.calculate_route, name="calculate_route"),
 path("smart-connect/", views.smart_connect, name="smart_connect"),
 path("search/", views.search_places, name="search_places"),
 path("nearby/", views.nearby_places, name="nearby_places"),
 path("weather/", views.weather, name="weather"),
 path("awareness/", views.awareness, name="awareness"),
 path("train-schedule/", views.train_schedule, name="train_schedule"),
]

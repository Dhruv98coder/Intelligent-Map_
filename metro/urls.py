from django.urls import path
from . import views
urlpatterns=[
 path("",views.metro_map,name="metro_map"),
 path("stations/",views.station_search,name="station_search"),
 path("route/",views.metro_route,name="metro_route"),
 path("walk/",views.metro_walk_route,name="metro_walk_route"),
]

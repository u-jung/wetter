from django.contrib import admin
from django.urls import path
from . import views
from django.conf import settings

app_name="wetter"
urlpatterns = [
    path('', views.index, name='index'),
    path('daten/<geo>/<monattag>/', views.daten, name='daten'),
    path("plz/", views.plz, name='plz'),
    path("monattage/", views.monattage, name='monattage')
]


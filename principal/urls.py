from django.urls import path
from . import views

app_name = "principal"

urlpatterns = [
    path("", views.home, name="principal"),
    path("panel_doctor/", views.panel_doctor, name="panel_doctor"),
    path("panel_admin/", views.panel_admin, name="panel_admin"),
    path("ayuda/", views.ayuda, name="ayuda"),
]
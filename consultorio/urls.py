from django.urls import path
from . import views

urlpatterns = [
    path("", views.seleccionar_region, name="consultorio"),
    path("obtener_comunas/<int:c_reg>/", views.obtener_comunas, name="obtener_comunas"),
    path("obtener_consultorios/<str:c_com>/", views.obtener_consultorios, name="obtener_consultorios"),
]

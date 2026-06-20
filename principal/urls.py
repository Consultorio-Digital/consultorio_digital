from django.urls import path
from . import views

app_name = "principal"

urlpatterns = [
    path("", views.home, name="principal"),
    path("panel_doctor/", views.panel_doctor, name="panel_doctor"),
    path("panel_admin/", views.panel_admin, name="panel_admin"),
    path("panel_admin/reserva/", views.admin_actualizar_reserva, name="admin_actualizar_reserva"),
    path("panel_admin/cuenta/", views.admin_toggle_cuenta, name="admin_toggle_cuenta"),
    path("panel_admin/exportar/reservas/", views.admin_exportar_reservas, name="admin_exportar_reservas"),
    path("ayuda/", views.ayuda, name="ayuda"),
]
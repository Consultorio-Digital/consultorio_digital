from django.contrib import admin

from .models import (
    Usuario, Profesional, Paciente, Administrador,
    Reserva, Consultorio, Disponibilidad,
)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ['rut', 'nombre', 'apellido', 'correo']
    search_fields = ['rut', 'nombre', 'apellido']


@admin.register(Profesional)
class ProfesionalAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'especialidad', 'consultorio']


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'ingreso']


@admin.register(Administrador)
class AdministradorAdmin(admin.ModelAdmin):
    list_display = ['usuario']


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ['paciente', 'profesional', 'fecha_reserva', 'estado']
    list_filter = ['estado']
    search_fields = ['paciente__usuario__rut']


@admin.register(Consultorio)
class ConsultorioAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'nom_com', 'nom_reg']
    search_fields = ['nombre', 'nom_com']


@admin.register(Disponibilidad)
class DisponibilidadAdmin(admin.ModelAdmin):
    list_display = ['profesional', 'fecha', 'hora_inicio', 'hora_fin']

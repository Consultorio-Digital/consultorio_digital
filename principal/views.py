# principal/views.py
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Min
from django.utils import timezone
from consultorio.models import Reserva, Profesional, Administrador, Paciente, Disponibilidad, Consultorio

def home(request: HttpRequest):
    if not request.user.is_authenticated:
        return redirect('login')

    if Administrador.objects.filter(usuario__rut=request.user.username).first():
        return redirect('principal:panel_admin')

    if Profesional.objects.filter(usuario__rut=request.user.username).exists():
        return redirect('principal:panel_doctor')

    reservas = []

    if request.user.is_authenticated:
        try:
            hoy = timezone.localdate()
            reservas = (
                Reserva.objects
                .filter(paciente__usuario__rut=request.user.username)
                .filter(
                    # Citas activas con fecha de hoy en adelante
                    Q(estado__in=['pendiente', 'confirmada'],
                      fecha_reserva__date__gte=hoy)
                    |
                    # Seguimientos con fecha de seguimiento pendiente
                    Q(estado='seguimiento',
                      fecha_seguimiento__gte=hoy)
                )
                .select_related('consultorio', 'profesional__usuario')
                .order_by('fecha_reserva')
            )
        except Exception:
            reservas = []

    confirmacion = request.session.pop('reserva_confirmada', None)

    return render(
        request=request,
        template_name="principal.html",
        context={
            "title"       : "Página principal",
            "reservas"    : reservas,
            "confirmacion": confirmacion,
        }
    )


@login_required(login_url='/login/')
def panel_doctor(request: HttpRequest):
    profesional = (
        Profesional.objects
        .select_related('usuario', 'consultorio')
        .filter(usuario__rut=request.user.username)
        .first()
    )

    # Solo los profesionales acceden a su panel; el resto vuelve al inicio.
    if profesional is None:
        return redirect('/')

    ahora = timezone.now()
    hoy   = timezone.localdate()

    # Próximas citas: futuras, activas (pendiente/confirmada), excluye canceladas/completadas.
    proximas_citas = (
        Reserva.objects
        .filter(
            profesional=profesional,
            fecha_reserva__gte=ahora,
            estado__in=['pendiente', 'confirmada'],
        )
        .select_related('paciente__usuario', 'consultorio')
        .order_by('fecha_reserva')
    )

    # Citas de hoy: cualquier estado excepto cancelada.
    citas_hoy = (
        Reserva.objects
        .filter(profesional=profesional, fecha_reserva__date=hoy)
        .exclude(estado='cancelada')
        .select_related('paciente__usuario', 'consultorio')
        .order_by('fecha_reserva')
    )

    total_pacientes_atendidos = Reserva.objects.filter(
        profesional=profesional, estado='completada'
    ).count()

    # Tarjetas de resumen.
    pendientes_hoy = citas_hoy.filter(estado__in=['pendiente', 'confirmada']).count()
    completadas_seguimiento = Reserva.objects.filter(
        profesional=profesional, estado__in=['completada', 'seguimiento']
    ).count()

    # Citas pasadas que quedaron sin gestionar (vencidas y aún activas).
    sin_gestionar = Reserva.objects.filter(
        profesional=profesional,
        fecha_reserva__lt=ahora,
        estado__in=['pendiente', 'confirmada'],
    ).count()

    disponibilidades = (
        Disponibilidad.objects
        .filter(profesional=profesional, fecha__gte=hoy)
        .order_by('fecha', 'hora_inicio')
    )

    # Historial completo (pasadas y futuras), lo más reciente primero.
    historial = (
        Reserva.objects
        .filter(profesional=profesional)
        .select_related('paciente__usuario', 'consultorio')
        .order_by('-fecha_reserva')[:50]
    )

    # Datos para el tab "Gestionar".
    regiones = (
        Consultorio.objects
        .values('c_reg')
        .annotate(nom_reg=Min('nom_reg'))
        .filter(nom_reg__isnull=False)
        .exclude(nom_reg='')
        .order_by('c_reg')
    )
    # Horas cada 30 min de 07:00 a 20:00 (inclusive).
    horas = [
        f"{h:02d}:{m:02d}"
        for h in range(7, 21)
        for m in (0, 30)
        if not (h == 20 and m == 30)
    ]

    return render(
        request=request,
        template_name="panel_doctor.html",
        context={
            "title"                     : "Panel del profesional",
            "profesional"               : profesional,
            "proximas_citas"            : proximas_citas,
            "citas_hoy"                 : citas_hoy,
            "total_pacientes_atendidos" : total_pacientes_atendidos,
            "pendientes_hoy"            : pendientes_hoy,
            "completadas_seguimiento"   : completadas_seguimiento,
            "sin_gestionar"             : sin_gestionar,
            "disponibilidades"          : disponibilidades,
            "historial"                 : historial,
            "hoy"                       : hoy,
            "regiones"                  : regiones,
            "horas"                     : horas,
        }
    )


def ayuda(request):
    return render(request, 'ayuda.html')


@login_required(login_url='/login/')
def panel_admin(request: HttpRequest):
    if not Administrador.objects.filter(usuario__rut=request.user.username).exists():
        return HttpResponse("No autorizado", status=403)

    reservas_por_estado = (
        Reserva.objects
        .values('estado')
        .annotate(total=Count('id'))
        .order_by('estado')
    )
    total_pacientes    = Paciente.objects.count()
    total_profesionales = Profesional.objects.count()

    ultimas_reservas = (
        Reserva.objects
        .select_related('paciente__usuario', 'profesional__usuario', 'consultorio')
        .order_by('-fecha_reserva')[:20]
    )

    # Profesionales por consultorio, con conteo de citas activas.
    profesionales = (
        Profesional.objects
        .select_related('usuario', 'consultorio')
        .annotate(
            citas_activas=Count(
                'reservas_confirmadas',
                filter=Q(reservas_confirmadas__estado__in=['pendiente', 'confirmada']),
            )
        )
        .order_by('consultorio__nombre', 'usuario__apellido')
    )

    return render(
        request=request,
        template_name="panel_admin.html",
        context={
            "title"              : "Panel del administrador",
            "reservas_por_estado": reservas_por_estado,
            "total_pacientes"    : total_pacientes,
            "total_profesionales": total_profesionales,
            "ultimas_reservas"   : ultimas_reservas,
            "profesionales"      : profesionales,
        }
    )
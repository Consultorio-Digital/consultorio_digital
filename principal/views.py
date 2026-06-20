# principal/views.py
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
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
    profesionales = list(
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

    # Estado de la cuenta auth.User de cada profesional (vinculada por RUT).
    ruts_activos = set(
        User.objects
        .filter(username__in=[p.usuario.rut for p in profesionales], is_active=True)
        .values_list('username', flat=True)
    )
    for p in profesionales:
        p.cuenta_activa = p.usuario.rut in ruts_activos

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
            "estado_choices"     : Reserva.ESTADO_CHOICES,
        }
    )


# ── Acciones del administrador ───────────────────────────────────────
def _es_admin(request: HttpRequest) -> bool:
    return Administrador.objects.filter(usuario__rut=request.user.username).exists()


# Estados que el admin puede asignar a cualquier reserva.
ESTADOS_ADMIN = {c[0] for c in Reserva.ESTADO_CHOICES}


@login_required(login_url='/login/')
def admin_actualizar_reserva(request: HttpRequest):
    """El admin cambia el estado de cualquier reserva (incluye cancelarla)."""
    if request.method != 'POST':
        return HttpResponse('Método no permitido', status=405)
    if not _es_admin(request):
        return HttpResponse('No autorizado', status=403)

    reserva = Reserva.objects.filter(id=request.POST.get('reserva_id')).first()
    if reserva is None:
        return HttpResponse('Reserva no encontrada', status=404)

    nuevo_estado = request.POST.get('nuevo_estado')
    if nuevo_estado not in ESTADOS_ADMIN:
        return HttpResponse('Estado no permitido', status=400)

    reserva.estado = nuevo_estado
    campos = ['estado']
    if nuevo_estado == 'cancelada':
        motivo = request.POST.get('motivo_cancelacion', '').strip()
        reserva.motivo_cancelacion = motivo or 'Cancelada por administración'
        campos.append('motivo_cancelacion')
    reserva.save(update_fields=campos)

    messages.success(
        request,
        f'Reserva #{reserva.id} actualizada a "{reserva.get_estado_display()}".'
    )
    return redirect('principal:panel_admin')


@login_required(login_url='/login/')
def admin_toggle_cuenta(request: HttpRequest):
    """El admin activa o desactiva una cuenta (bloquea/permite el login)."""
    if request.method != 'POST':
        return HttpResponse('Método no permitido', status=405)
    if not _es_admin(request):
        return HttpResponse('No autorizado', status=403)

    rut = (request.POST.get('rut') or '').strip()

    # Salvaguarda: el admin no puede desactivar su propia cuenta.
    if rut == request.user.username:
        messages.error(request, 'No puedes desactivar tu propia cuenta.')
        return redirect('principal:panel_admin')

    user = User.objects.filter(username=rut).first()
    if user is None:
        messages.error(request, 'Cuenta no encontrada.')
        return redirect('principal:panel_admin')

    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    messages.success(
        request,
        f'Cuenta {rut} {"activada" if user.is_active else "desactivada"}.'
    )
    return redirect('principal:panel_admin')


@login_required(login_url='/login/')
def admin_exportar_reservas(request: HttpRequest):
    """Exporta TODAS las reservas a CSV (no solo las 20 que muestra el panel)."""
    import csv

    if not _es_admin(request):
        return HttpResponse('No autorizado', status=403)

    hoy = timezone.localdate().strftime('%Y%m%d')
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="reservas_{hoy}.csv"'
    # BOM para que Excel reconozca UTF-8 (acentos del español).
    response.write('﻿')

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Paciente', 'RUT paciente', 'Profesional',
        'Consultorio', 'Comuna', 'Fecha', 'Hora', 'Estado', 'Motivo',
    ])

    reservas = (
        Reserva.objects
        .select_related('paciente__usuario', 'profesional__usuario', 'consultorio')
        .order_by('-fecha_reserva')
    )
    for r in reservas:
        fecha_local = timezone.localtime(r.fecha_reserva)
        pac = r.paciente.usuario
        prof = r.profesional.usuario if r.profesional else None
        writer.writerow([
            r.id,
            f'{pac.nombre} {pac.apellido}',
            pac.rut,
            f'{prof.nombre} {prof.apellido}' if prof else '',
            r.consultorio.nombre,
            r.consultorio.nom_com,
            fecha_local.strftime('%d/%m/%Y'),
            fecha_local.strftime('%H:%M'),
            r.get_estado_display(),
            r.motivo,
        ])

    return response
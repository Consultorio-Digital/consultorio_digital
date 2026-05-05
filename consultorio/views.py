from datetime import datetime, date, timedelta

from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Min
from django.utils import timezone

from .models import Consultorio, Reserva, Usuario, Paciente, Profesional, Disponibilidad

# ---------------------------------------------------------------------------
# NOTAS DE DESARROLLO — restricciones pendientes de producción
# ---------------------------------------------------------------------------
# 1. FECHAS EN EL PASADO: actualmente el flujo de reserva (paciente) y la
#    declaración de disponibilidad (doctor) permiten seleccionar fechas y
#    horarios pasados. Esto es intencional para facilitar pruebas.
#    En producción se deberá validar que fecha_reserva >= now() en la vista
#    `seleccionar_region` y que la fecha de disponibilidad >= hoy en
#    `panel_doctor` (action='disponibilidad').
#
# 2. CÓDIGO DE CANCELACIÓN: el código de 6 dígitos se genera y muestra
#    directamente en pantalla. En producción debería enviarse al correo
#    registrado del paciente y no mostrarse en la interfaz.
# ---------------------------------------------------------------------------


@login_required(login_url='/login/')
def seleccionar_region(request):
    if request.method == 'POST':
        consultorio_id = request.POST.get('consultorio')
        profesional_id = request.POST.get('profesional_id')
        motivo         = request.POST.get('motivo', '').strip()
        slot           = request.POST.get('slot')  # "YYYY-MM-DD HH:MM"

        try:
            fecha_reserva = datetime.strptime(slot, "%Y-%m-%d %H:%M")
            if timezone.is_naive(fecha_reserva):
                fecha_reserva = timezone.make_aware(fecha_reserva)

            u = request.user
            usuario, _ = Usuario.objects.get_or_create(
                rut=u.username,
                defaults={
                    'nombre'           : u.first_name or u.username,
                    'apellido'         : u.last_name or '',
                    'fecha_nacimiento' : date.today(),
                    'correo'           : u.email or '',
                },
            )
            paciente, _ = Paciente.objects.get_or_create(
                usuario=usuario,
                defaults={'ingreso': date.today()},
            )
            consultorio  = Consultorio.objects.get(objectid=consultorio_id)
            profesional  = Profesional.objects.select_related('usuario').get(id=profesional_id)

            # Verificar que el slot sigue disponible (evitar doble reserva)
            slot_tomado = Reserva.objects.filter(
                profesional=profesional,
                fecha_reserva=fecha_reserva,
            ).exclude(estado='cancelada').exists()

            if not slot_tomado:
                Reserva.objects.create(
                    consultorio=consultorio,
                    paciente=paciente,
                    profesional=profesional,
                    fecha_reserva=fecha_reserva,
                    motivo=motivo,
                )

            doctor_nombre = f"Dr/a. {profesional.usuario.nombre} {profesional.usuario.apellido}"
            request.session['reserva_confirmada'] = {
                'consultorio' : consultorio.nombre,
                'fecha'       : fecha_reserva.strftime("%d/%m/%Y"),
                'hora'        : fecha_reserva.strftime("%H:%M"),
                'doctor'      : doctor_nombre,
                'ya_tomado'   : slot_tomado,
            }
        except Exception as e:
            print(f"Error al crear reserva: {e}")

        return redirect('principal:principal')

    regiones = (
        Consultorio.objects
        .values('c_reg')
        .annotate(nom_reg=Min('nom_reg'))
        .filter(nom_reg__isnull=False)
        .exclude(nom_reg='')
        .order_by('c_reg')
    )
    return render(request, 'consultorio.html', {'regiones': regiones})


# ── Historial de citas de un paciente (para el doctor) ───────────────

@login_required(login_url='/login/')
def historial_paciente(request):
    """Devuelve JSON con datos de contacto y citas previas de un paciente,
    solo visibles para doctores. No incluye información clínica."""
    paciente_id    = request.GET.get('paciente_id')
    consultorio_id = request.GET.get('consultorio_id')

    # Solo doctores pueden consultar esto
    if not Profesional.objects.filter(usuario__rut=request.user.username).exists():
        return JsonResponse({'error': 'No autorizado'}, status=403)

    try:
        paciente = Paciente.objects.select_related('usuario').get(id=paciente_id)
    except Paciente.DoesNotExist:
        return JsonResponse({'error': 'Paciente no encontrado'}, status=404)

    u = paciente.usuario
    citas = (
        Reserva.objects
        .filter(paciente=paciente, consultorio_id=consultorio_id)
        .order_by('-fecha_reserva')
        .values(
            'id', 'fecha_reserva', 'motivo', 'estado',
            'notas_doctor', 'fecha_seguimiento',
        )
    )

    citas_lista = []
    for c in citas:
        citas_lista.append({
            'fecha'        : c['fecha_reserva'].strftime('%d/%m/%Y %H:%M'),
            'motivo'       : c['motivo'],
            'estado'       : c['estado'],
            'instruccion'  : c['notas_doctor'] or '',
            'seguimiento'  : c['fecha_seguimiento'].strftime('%d/%m/%Y') if c['fecha_seguimiento'] else '',
        })

    return JsonResponse({
        'nombre'   : f"{u.nombre} {u.apellido}",
        'rut'      : u.rut,
        'correo'   : u.correo,
        'telefono' : u.telefono or '',
        'citas'    : citas_lista,
    })


# ── Endpoints AJAX para el flujo de reserva ──────────────────────────

@login_required(login_url='/login/')
def obtener_doctores(request):
    """Doctores que trabajan en un consultorio dado."""
    consultorio_id = request.GET.get('consultorio_id')
    if not consultorio_id:
        return JsonResponse([], safe=False)

    doctores = (
        Profesional.objects
        .filter(consultorio_id=consultorio_id)
        .select_related('usuario')
        .order_by('usuario__apellido', 'usuario__nombre')
    )
    data = [
        {
            'id'          : d.id,
            'nombre'      : f"{d.usuario.nombre} {d.usuario.apellido}",
            'especialidad': d.especialidad,
        }
        for d in doctores
    ]
    return JsonResponse(data, safe=False)


@login_required(login_url='/login/')
def obtener_fechas(request):
    """Fechas con disponibilidad declarada para un profesional (hoy en adelante)."""
    profesional_id = request.GET.get('profesional_id')
    if not profesional_id:
        return JsonResponse([], safe=False)

    hoy    = timezone.localdate()
    fechas = (
        Disponibilidad.objects
        .filter(profesional_id=profesional_id, fecha__gte=hoy)
        .values_list('fecha', flat=True)
        .distinct()
        .order_by('fecha')
    )
    return JsonResponse([str(f) for f in fechas], safe=False)


@login_required(login_url='/login/')
def obtener_slots(request):
    """Slots de 30 min libres para un profesional en una fecha."""
    profesional_id = request.GET.get('profesional_id')
    fecha_str      = request.GET.get('fecha')

    if not profesional_id or not fecha_str:
        return JsonResponse([], safe=False)

    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse([], safe=False)

    disponibilidades = Disponibilidad.objects.filter(
        profesional_id=profesional_id,
        fecha=fecha,
    )

    # Generar todos los slots posibles (bloques de 30 min)
    all_slots = []
    for disp in disponibilidades:
        current = datetime.combine(fecha, disp.hora_inicio)
        end     = datetime.combine(fecha, disp.hora_fin)
        while current < end:
            all_slots.append(current)
            current += timedelta(minutes=30)

    # Slots ya ocupados
    taken_qs = (
        Reserva.objects
        .filter(profesional_id=profesional_id, fecha_reserva__date=fecha)
        .exclude(estado='cancelada')
        .values_list('fecha_reserva', flat=True)
    )
    taken_times = {timezone.localtime(dt).strftime("%H:%M") for dt in taken_qs}

    free = [
        {'value': s.strftime("%Y-%m-%d %H:%M"), 'label': s.strftime("%H:%M")}
        for s in all_slots
        if s.strftime("%H:%M") not in taken_times
    ]
    return JsonResponse(free, safe=False)

@login_required(login_url='/login/')
def obtener_comunas(request, c_reg):
    comunas = (
        Consultorio
        .objects
        .filter(c_reg=c_reg)
        .values('c_com', 'nom_com')
        .distinct()
        .order_by('nom_com')
    )
    return JsonResponse(list(comunas), safe=False)

@login_required(login_url='/login/')
def obtener_consultorios(request, c_com):
    consultorios = (
        Consultorio
        .objects
        .filter(c_com=c_com)
        .values()
    )
    return JsonResponse(list(consultorios), safe=False)

# Create your views here.
def home(request: HttpRequest):
    return render(
        request = request, 
        template_name = "consultorio.html", 
        context = {"title": "Página principal del consultorio"}
    )

@login_required(login_url='/login/')
def mis_horas(request: HttpRequest):
    from django.core.paginator import Paginator

    try:
        from django.db.models import Q
        hoy = timezone.localdate()
        # Historial: todo lo que NO está en "Próximas citas"
        qs = (
            Reserva.objects
            .filter(paciente__usuario__rut=request.user.username)
            .exclude(
                Q(estado__in=['pendiente', 'confirmada'],
                  fecha_reserva__date__gte=hoy)
                |
                Q(estado='seguimiento',
                  fecha_seguimiento__gte=hoy)
            )
            .select_related('consultorio', 'profesional__usuario')
            .order_by('-fecha_reserva')
        )
    except Exception:
        qs = Reserva.objects.none()

    paginator = Paginator(qs, 15)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(
        request=request,
        template_name="mis_horas.html",
        context={"title": "Historial de citas", "page_obj": page_obj},
    )

@login_required(login_url='/login/')
def reservar_hora(request: HttpRequest):
    return render(
        request = request, 
        template_name = "reservar_hora.html", 
        context = {"title": "Reservar hora"}
    )

@login_required(login_url='/login/')
def cancelar_hora(request: HttpRequest):
    import random

    if request.method == 'POST':
        action = request.POST.get('action')

        # ── Paso 1: selección de cita → generar código y guardarlo en sesión ──
        if action == 'seleccionar':
            reserva_id = request.POST.get('reserva_id')
            if reserva_id:
                codigo = f"{random.randint(0, 999999):06d}"
                request.session['cancelacion'] = {
                    'reserva_id': reserva_id,
                    'codigo'    : codigo,
                }
            return redirect('cancelar_hora')

        # ── Limpiar sesión → volver al paso 1 ──
        if action == 'limpiar':
            request.session.pop('cancelacion', None)
            request.session.pop('codigo_incorrecto', None)
            return redirect('cancelar_hora')

        # ── Paso 2: verificar código → cancelar o rechazar ──
        if action == 'confirmar':
            cancelacion  = request.session.get('cancelacion', {})
            confirmar_id = request.POST.get('confirmar_reserva_id')
            codigo_input = request.POST.get('codigo', '').strip()
            motivo_can   = request.POST.get('motivo_cancelacion', '').strip()

            if (
                str(cancelacion.get('reserva_id')) == str(confirmar_id)
                and cancelacion.get('codigo') == codigo_input
            ):
                try:
                    reserva = Reserva.objects.get(
                        id=confirmar_id,
                        paciente__usuario__rut=request.user.username,
                    )
                    reserva.estado             = 'cancelada'
                    reserva.motivo_cancelacion = motivo_can or None
                    reserva.save()
                except Reserva.DoesNotExist:
                    pass
                request.session.pop('cancelacion', None)
                request.session['reserva_cancelada'] = True
                return redirect('principal:principal')
            else:
                # Código incorrecto: volver al paso 2 con error
                request.session['codigo_incorrecto'] = True
                return redirect('cancelar_hora')

    # ── GET: renderizar según estado de sesión ──
    cancelacion       = request.session.get('cancelacion')
    codigo_incorrecto = request.session.pop('codigo_incorrecto', False)

    try:
        reservas_activas = (
            Reserva.objects
            .filter(
                paciente__usuario__rut=request.user.username,
                estado__in=['pendiente', 'confirmada'],
            )
            .select_related('consultorio', 'profesional__usuario')
            .order_by('fecha_reserva')
        )
    except Exception:
        reservas_activas = []

    reserva_seleccionada = None
    codigo_generado      = None

    if cancelacion:
        rid = cancelacion.get('reserva_id')
        reserva_seleccionada = Reserva.objects.filter(
            id=rid,
            paciente__usuario__rut=request.user.username,
        ).select_related('consultorio', 'profesional__usuario').first()
        codigo_generado = cancelacion.get('codigo')

    return render(request, 'cancelar_hora.html', {
        'title'               : 'Cancelar hora',
        'reservas_activas'    : reservas_activas,
        'reserva_seleccionada': reserva_seleccionada,
        'codigo_generado'     : codigo_generado,
        'codigo_incorrecto'   : codigo_incorrecto,
    })

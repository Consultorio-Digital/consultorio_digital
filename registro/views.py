from datetime import date

from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.db.models import Min

from consultorio.models import Usuario, Paciente, Profesional, Consultorio
from .forms import RegisterForm


def registro(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user         = form.save()
            tipo         = form.cleaned_data.get("tipo")
            especialidad = form.cleaned_data.get("especialidad", "")

            usuario, _ = Usuario.objects.get_or_create(
                rut=user.username,
                defaults={
                    'nombre'           : user.first_name or user.username,
                    'apellido'         : user.last_name or '',
                    'fecha_nacimiento' : date.today(),
                    'correo'           : user.email or '',
                },
            )

            # Persistir los datos de contacto que vienen del formulario pero que
            # auth.User no almacena (dirección, teléfono y fecha de nacimiento).
            usuario.direccion = form.cleaned_data.get("address") or None
            usuario.telefono  = form.cleaned_data.get("phone") or None
            birthdate = form.cleaned_data.get("birthdate")
            if birthdate:
                usuario.fecha_nacimiento = birthdate
            usuario.save()

            if tipo == 'profesional':
                profesional, _ = Profesional.objects.get_or_create(
                    usuario=usuario,
                    defaults={'especialidad': especialidad or 'General'},
                )
                # Recinto opcional elegido en la cascada región→comuna→consultorio.
                consultorio_id = form.cleaned_data.get('consultorio')
                if consultorio_id:
                    consultorio = Consultorio.objects.filter(objectid=consultorio_id).first()
                    if consultorio:
                        profesional.consultorio = consultorio
                        profesional.save(update_fields=['consultorio'])
            else:
                Paciente.objects.get_or_create(
                    usuario=usuario,
                    defaults={'ingreso': date.today()},
                )

            raw_password = form.cleaned_data.get("password1")
            user = authenticate(username=user.username, password=raw_password)
            login(request, user)
            return redirect("/")

        else:
            print(form.errors)

    else:
        form = RegisterForm()

    # Regiones para la cascada de recinto (registro de profesional).
    regiones = (
        Consultorio.objects
        .values('c_reg')
        .annotate(nom_reg=Min('nom_reg'))
        .filter(nom_reg__isnull=False)
        .exclude(nom_reg='')
        .order_by('c_reg')
    )

    return render(
        request=request,
        template_name="registro.html",
        context={"form": form, "title": "Crea tu cuenta", "regiones": regiones},
    )
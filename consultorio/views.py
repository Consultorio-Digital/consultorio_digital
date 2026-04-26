from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from .models import Consultorio


@login_required(login_url='/login/')
def seleccionar_region(request):
    regiones = (
        Consultorio
        .objects
        .values('c_reg', 'nom_reg')
        .distinct()
        .order_by('c_reg')
    )
    return render(request, 'consultorio.html', {'regiones': regiones})


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

from datetime import date, time

from django.test import TestCase

from .models import (
    Consultorio,
    Disponibilidad,
    Paciente,
    Profesional,
    Reserva,
    Usuario,
)


# ---------------------------------------------------------------------------
# Helpers para crear objetos de prueba
# ---------------------------------------------------------------------------

def _crear_consultorio(objectid=1, nombre="CESFAM Test", c_com="05101"):
    return Consultorio.objects.create(
        objectid  = objectid,
        nombre    = nombre,
        c_reg     = 5.0,
        nom_reg   = "Region de Valparaiso",
        c_com     = c_com,
        nom_com   = "Valparaiso",
        c_ant     = "", c_vig=1.0, c_mad="", c_nmad="",
        c_depend  = 1.0,
        depen     = "Municipal",
        perenec   = "SNSS",
        tipo      = "CESFAM",
        ambito    = "Urbano",
        urgencia  = "No",
        certifica = "No",
        depen_a   = "Municipal",
        nivel     = "Primario",
        via       = "Calle",
        numero    = "100",
        direccion = "Calle Principal 100",
        fono      = None,
        f_inicio  = 2000.0,
        f_reaper  = "",
        sapu      = "No",
        f_cambio  = "",
        tipo_camb = "",
        prestador = "Municipal",
        estado    = "Activo",
        nivel_com = "Primario",
        modalidad = "Presencial",
        latitud   = -33.05,
        longitud  = -71.62,
    )


def _crear_usuario(rut="123456785", nombre="Ana", apellido="Perez",
                   correo="ana@test.cl"):
    return Usuario.objects.create(
        rut             = rut,
        nombre          = nombre,
        apellido        = apellido,
        fecha_nacimiento= date(1990, 1, 15),
        correo          = correo,
    )


def _crear_profesional(rut="987654321", consultorio=None):
    usuario = _crear_usuario(
        rut=rut, nombre="Carlos", apellido="Lopez", correo="carlos@cesfam.cl"
    )
    return Profesional.objects.create(
        usuario      = usuario,
        especialidad = "Medicina General",
        consultorio  = consultorio,
    )


# ---------------------------------------------------------------------------
# ConsultorioModelTests
# ---------------------------------------------------------------------------

class ConsultorioModelTests(TestCase):
    """Pruebas unitarias para el modelo Consultorio."""

    def setUp(self):
        self.consultorio = _crear_consultorio()

    def test_str_retorna_nombre(self):
        self.assertEqual(str(self.consultorio), "CESFAM Test")

    def test_ordering_alfabetico_por_nombre(self):
        _crear_consultorio(objectid=2, nombre="CESFAM Angamos")
        _crear_consultorio(objectid=3, nombre="CESFAM Zonal Norte")
        nombres = list(Consultorio.objects.values_list("nombre", flat=True))
        self.assertEqual(nombres, sorted(nombres))

    def test_fono_puede_ser_nulo(self):
        self.assertIsNone(self.consultorio.fono)

    def test_primary_key_es_objectid(self):
        recuperado = Consultorio.objects.get(pk=1)
        self.assertEqual(recuperado.nombre, "CESFAM Test")


# ---------------------------------------------------------------------------
# UsuarioModelTests
# ---------------------------------------------------------------------------

class UsuarioModelTests(TestCase):
    """Pruebas unitarias para el modelo Usuario."""

    def setUp(self):
        self.usuario = _crear_usuario()

    def test_str_retorna_rut(self):
        self.assertEqual(str(self.usuario), "123456785")

    def test_primary_key_es_rut(self):
        recuperado = Usuario.objects.get(pk="123456785")
        self.assertEqual(recuperado.nombre, "Ana")

    def test_telefono_puede_ser_nulo(self):
        self.assertIsNone(self.usuario.telefono)


# ---------------------------------------------------------------------------
# ReservaModelTests
# ---------------------------------------------------------------------------

class ReservaModelTests(TestCase):
    """Pruebas unitarias para el modelo Reserva."""

    def setUp(self):
        from django.utils import timezone
        self.consultorio = _crear_consultorio()
        self.usuario     = _crear_usuario()
        self.paciente    = Paciente.objects.create(
            usuario = self.usuario,
            ingreso = date(2026, 1, 1),
        )
        self.reserva = Reserva.objects.create(
            consultorio  = self.consultorio,
            paciente     = self.paciente,
            fecha_reserva= timezone.now(),
            motivo       = "Control general",
        )

    def test_estado_por_defecto_es_pendiente(self):
        self.assertEqual(self.reserva.estado, "pendiente")

    def test_estados_disponibles(self):
        estados = [c[0] for c in Reserva.ESTADO_CHOICES]
        for esperado in ("pendiente", "confirmada", "completada",
                         "seguimiento", "cancelada", "no_asistio"):
            self.assertIn(esperado, estados)

    def test_str_contiene_nombre_consultorio_y_paciente(self):
        s = str(self.reserva)
        self.assertIn("CESFAM Test", s)
        self.assertIn("123456785", s)

    def test_notas_doctor_puede_ser_nulo(self):
        self.assertIsNone(self.reserva.notas_doctor)

    def test_fecha_seguimiento_puede_ser_nula(self):
        self.assertIsNone(self.reserva.fecha_seguimiento)

    def test_motivo_cancelacion_puede_ser_nulo(self):
        self.assertIsNone(self.reserva.motivo_cancelacion)

    def test_puede_cambiar_estado_a_cancelada(self):
        self.reserva.estado = "cancelada"
        self.reserva.save()
        actualizada = Reserva.objects.get(pk=self.reserva.pk)
        self.assertEqual(actualizada.estado, "cancelada")


# ---------------------------------------------------------------------------
# ProfesionalModelTests
# ---------------------------------------------------------------------------

class ProfesionalModelTests(TestCase):
    """Pruebas unitarias para el modelo Profesional."""

    def setUp(self):
        self.consultorio = _crear_consultorio()
        self.profesional = _crear_profesional(consultorio=self.consultorio)

    def test_str_retorna_rut_del_usuario(self):
        self.assertEqual(str(self.profesional), "987654321")

    def test_consultorio_puede_ser_nulo(self):
        prof = _crear_profesional(rut="111111115", consultorio=None)
        self.assertIsNone(prof.consultorio)


# ---------------------------------------------------------------------------
# DisponibilidadModelTests
# ---------------------------------------------------------------------------

class DisponibilidadModelTests(TestCase):
    """Pruebas unitarias para el modelo Disponibilidad."""

    def setUp(self):
        self.consultorio = _crear_consultorio()
        self.profesional = _crear_profesional(consultorio=self.consultorio)

    def test_str_contiene_profesional_y_fecha(self):
        disp = Disponibilidad.objects.create(
            profesional = self.profesional,
            fecha       = date(2026, 6, 1),
            hora_inicio = time(9, 0),
            hora_fin    = time(13, 0),
        )
        s = str(disp)
        self.assertIn("2026-06-01", s)

    def test_unique_together_profesional_fecha_hora_inicio(self):
        from django.db import IntegrityError
        Disponibilidad.objects.create(
            profesional = self.profesional,
            fecha       = date(2026, 6, 2),
            hora_inicio = time(14, 0),
            hora_fin    = time(18, 0),
        )
        with self.assertRaises(IntegrityError):
            Disponibilidad.objects.create(
                profesional = self.profesional,
                fecha       = date(2026, 6, 2),
                hora_inicio = time(14, 0),
                hora_fin    = time(16, 0),
            )

    def test_ordering_por_fecha_luego_hora_inicio(self):
        Disponibilidad.objects.create(
            profesional=self.profesional,
            fecha=date(2026, 6, 3),
            hora_inicio=time(14, 0),
            hora_fin=time(18, 0),
        )
        Disponibilidad.objects.create(
            profesional=self.profesional,
            fecha=date(2026, 6, 3),
            hora_inicio=time(9, 0),
            hora_fin=time(13, 0),
        )
        fechas_horas = list(
            Disponibilidad.objects.values_list("fecha", "hora_inicio")
        )
        self.assertEqual(
            fechas_horas,
            sorted(fechas_horas, key=lambda x: (x[0], x[1]))
        )


# ---------------------------------------------------------------------------
# ConsultorioViewAuthTests — vistas que requieren autenticacion
# ---------------------------------------------------------------------------

class ConsultorioViewAuthTests(TestCase):
    """Verifica que las vistas protegidas redirigen a login si no hay sesion."""

    def test_seleccionar_region_redirige_sin_login(self):
        response = self.client.get("/consultorio/")
        self.assertRedirects(
            response, "/login/?next=/consultorio/",
            fetch_redirect_response=False,
        )

    def test_mis_horas_redirige_sin_login(self):
        response = self.client.get("/consultorio/mis_horas")
        self.assertRedirects(
            response, "/login/?next=/consultorio/mis_horas",
            fetch_redirect_response=False,
        )

    def test_cancelar_hora_redirige_sin_login(self):
        response = self.client.get("/consultorio/cancelar_hora")
        self.assertRedirects(
            response, "/login/?next=/consultorio/cancelar_hora",
            fetch_redirect_response=False,
        )

    def test_historial_paciente_redirige_sin_login(self):
        response = self.client.get("/consultorio/historial_paciente/")
        self.assertRedirects(
            response, "/login/?next=/consultorio/historial_paciente/",
            fetch_redirect_response=False,
        )


class ConsultorioViewGetTests(TestCase):
    """Verifica respuestas GET para usuarios autenticados."""

    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(
            username="111111118",
            password="clave_prueba_2026",
        )
        self.client.login(username="111111118", password="clave_prueba_2026")

    def test_seleccionar_region_retorna_200(self):
        response = self.client.get("/consultorio/")
        self.assertEqual(response.status_code, 200)

    def test_mis_horas_retorna_200(self):
        response = self.client.get("/consultorio/mis_horas")
        self.assertEqual(response.status_code, 200)

    def test_cancelar_hora_retorna_200(self):
        response = self.client.get("/consultorio/cancelar_hora")
        self.assertEqual(response.status_code, 200)

    def test_obtener_comunas_sin_region_retorna_lista_vacia(self):
        response = self.client.get("/consultorio/obtener_comunas/99/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_obtener_consultorios_sin_resultados_retorna_lista_vacia(self):
        response = self.client.get("/consultorio/obtener_consultorios/XXXXX/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_obtener_doctores_sin_consultorio_retorna_lista_vacia(self):
        response = self.client.get("/consultorio/obtener_doctores/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_obtener_fechas_sin_profesional_retorna_lista_vacia(self):
        response = self.client.get("/consultorio/obtener_fechas/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_obtener_slots_sin_parametros_retorna_lista_vacia(self):
        response = self.client.get("/consultorio/obtener_slots/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])


# ---------------------------------------------------------------------------
# FlujoReservaFuncionalTests — EDT 5.2 Prueba Funcional
# ---------------------------------------------------------------------------

class FlujoReservaFuncionalTests(TestCase):
    """Pruebas funcionales del flujo completo de reserva de hora medica."""

    def setUp(self):
        from django.contrib.auth.models import User

        self.user = User.objects.create_user(
            username   = "333333334",
            password   = "clave_prueba_2026",
            first_name = "Maria",
            last_name  = "Silva",
            email      = "maria@test.cl",
        )
        self.consultorio = _crear_consultorio(objectid=200, c_com="05101")
        self.profesional = _crear_profesional(
            rut="444444448", consultorio=self.consultorio
        )
        Disponibilidad.objects.create(
            profesional = self.profesional,
            fecha       = date(2026, 7, 1),
            hora_inicio = time(9, 0),
            hora_fin    = time(11, 0),
        )
        self.client.login(username="333333334", password="clave_prueba_2026")

    # — Endpoints AJAX ——————————————————————————————————————————————————————

    def test_obtener_comunas_retorna_com_del_consultorio(self):
        response = self.client.get("/consultorio/obtener_comunas/5/")
        self.assertEqual(response.status_code, 200)
        comunas = response.json()
        self.assertTrue(any(c["c_com"] == "05101" for c in comunas))

    def test_obtener_consultorios_filtra_por_comuna(self):
        response = self.client.get("/consultorio/obtener_consultorios/05101/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["nombre"], "CESFAM Test")

    def test_obtener_doctores_retorna_profesional_del_consultorio(self):
        response = self.client.get(
            f"/consultorio/obtener_doctores/?consultorio_id={self.consultorio.objectid}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertIn("Carlos", data[0]["nombre"])
        self.assertEqual(data[0]["especialidad"], "Medicina General")

    def test_obtener_fechas_retorna_dias_con_disponibilidad(self):
        response = self.client.get(
            f"/consultorio/obtener_fechas/?profesional_id={self.profesional.id}"
        )
        self.assertEqual(response.status_code, 200)
        fechas = response.json()
        self.assertIn("2026-07-01", fechas)

    def test_obtener_slots_genera_bloques_de_30_minutos(self):
        response = self.client.get(
            f"/consultorio/obtener_slots/"
            f"?profesional_id={self.profesional.id}&fecha=2026-07-01"
        )
        self.assertEqual(response.status_code, 200)
        slots  = response.json()
        # 09:00 a 11:00 = 4 slots de 30 min
        self.assertEqual(len(slots), 4)
        labels = [s["label"] for s in slots]
        self.assertIn("09:00", labels)
        self.assertIn("09:30", labels)
        self.assertIn("10:00", labels)
        self.assertIn("10:30", labels)

    # — Flujo de reserva ————————————————————————————————————————————————————

    def test_post_reserva_crea_registro_y_redirige_al_inicio(self):
        response = self.client.post("/consultorio/", {
            "consultorio"  : self.consultorio.objectid,
            "profesional_id": self.profesional.id,
            "motivo"       : "Control de rutina",
            "slot"         : "2026-07-01 09:00",
        })
        self.assertRedirects(
            response, "/",
            fetch_redirect_response=False,
        )
        self.assertTrue(
            Reserva.objects.filter(motivo="Control de rutina").exists()
        )

    def test_reserva_queda_en_estado_pendiente_por_defecto(self):
        self.client.post("/consultorio/", {
            "consultorio"  : self.consultorio.objectid,
            "profesional_id": self.profesional.id,
            "motivo"       : "Primera consulta",
            "slot"         : "2026-07-01 09:30",
        })
        reserva = Reserva.objects.get(motivo="Primera consulta")
        self.assertEqual(reserva.estado, "pendiente")

    def test_slot_ocupado_no_genera_reserva_duplicada(self):
        from django.utils import timezone
        import datetime

        slot_dt = timezone.make_aware(datetime.datetime(2026, 7, 1, 10, 0))
        # Crear reserva preexistente para ese slot
        usuario_otro = _crear_usuario(
            rut="555555557", nombre="Luis", apellido="Vega", correo="luis@t.cl"
        )
        paciente_otro = Paciente.objects.create(
            usuario=usuario_otro, ingreso=date(2026, 1, 1)
        )
        Reserva.objects.create(
            consultorio  = self.consultorio,
            paciente     = paciente_otro,
            profesional  = self.profesional,
            fecha_reserva= slot_dt,
            motivo       = "Reserva previa",
        )
        # Segundo intento de reserva para el mismo slot
        self.client.post("/consultorio/", {
            "consultorio"  : self.consultorio.objectid,
            "profesional_id": self.profesional.id,
            "motivo"       : "Intento duplicado",
            "slot"         : "2026-07-01 10:00",
        })
        count = Reserva.objects.filter(
            profesional  = self.profesional,
            fecha_reserva= slot_dt,
        ).exclude(estado="cancelada").count()
        self.assertEqual(count, 1)

    def test_slot_ocupado_guarda_ya_tomado_en_sesion(self):
        from django.utils import timezone
        import datetime

        slot_dt = timezone.make_aware(datetime.datetime(2026, 7, 1, 10, 30))
        usuario_otro = _crear_usuario(
            rut="666666660", nombre="Rosa", apellido="Diaz", correo="rosa@t.cl"
        )
        paciente_otro = Paciente.objects.create(
            usuario=usuario_otro, ingreso=date(2026, 1, 1)
        )
        Reserva.objects.create(
            consultorio  = self.consultorio,
            paciente     = paciente_otro,
            profesional  = self.profesional,
            fecha_reserva= slot_dt,
            motivo       = "Reserva ocupada",
        )
        self.client.post("/consultorio/", {
            "consultorio"  : self.consultorio.objectid,
            "profesional_id": self.profesional.id,
            "motivo"       : "Intento sobre slot ocupado",
            "slot"         : "2026-07-01 10:30",
        })
        sesion = self.client.session.get("reserva_confirmada", {})
        self.assertTrue(sesion.get("ya_tomado"))

    def test_slot_libre_guarda_ya_tomado_false_en_sesion(self):
        self.client.post("/consultorio/", {
            "consultorio"  : self.consultorio.objectid,
            "profesional_id": self.profesional.id,
            "motivo"       : "Cita nueva sin conflicto",
            "slot"         : "2026-07-01 09:00",
        })
        sesion = self.client.session.get("reserva_confirmada", {})
        self.assertFalse(sesion.get("ya_tomado"))


# ---------------------------------------------------------------------------
# CancelacionFuncionalTests
# ---------------------------------------------------------------------------

class CancelacionFuncionalTests(TestCase):
    """Pruebas funcionales del flujo de cancelacion de hora medica."""

    def setUp(self):
        from django.contrib.auth.models import User
        from django.utils import timezone

        self.user = User.objects.create_user(
            username="777777771",
            password="clave_prueba_2026",
        )
        self.consultorio = _crear_consultorio(objectid=300, c_com="05101")
        self.profesional = _crear_profesional(
            rut="888888886", consultorio=self.consultorio
        )
        usuario_paciente = _crear_usuario(
            rut="777777771", nombre="Pedro", apellido="Mora", correo="pedro@t.cl"
        )
        self.paciente = Paciente.objects.create(
            usuario=usuario_paciente, ingreso=date(2026, 1, 1)
        )
        self.reserva = Reserva.objects.create(
            consultorio  = self.consultorio,
            paciente     = self.paciente,
            profesional  = self.profesional,
            fecha_reserva= timezone.now(),
            motivo       = "Cita a cancelar",
            estado       = "confirmada",
        )
        self.client.login(username="777777771", password="clave_prueba_2026")

    def test_get_cancelar_hora_retorna_200_con_reservas(self):
        response = self.client.get("/consultorio/cancelar_hora")
        self.assertEqual(response.status_code, 200)
        self.assertIn("reservas_activas", response.context)

    def test_seleccionar_reserva_guarda_codigo_en_sesion(self):
        self.client.post("/consultorio/cancelar_hora", {
            "action"    : "seleccionar",
            "reserva_id": self.reserva.id,
        })
        sesion = self.client.session.get("cancelacion", {})
        self.assertEqual(str(sesion.get("reserva_id")), str(self.reserva.id))
        self.assertRegex(sesion.get("codigo", ""), r"^\d{6}$")

    def test_cancelacion_con_codigo_correcto_cambia_estado(self):
        # Paso 1: seleccionar
        self.client.post("/consultorio/cancelar_hora", {
            "action"    : "seleccionar",
            "reserva_id": self.reserva.id,
        })
        codigo = self.client.session["cancelacion"]["codigo"]

        # Paso 2: confirmar con codigo correcto
        self.client.post("/consultorio/cancelar_hora", {
            "action"             : "confirmar",
            "confirmar_reserva_id": self.reserva.id,
            "codigo"             : codigo,
            "motivo_cancelacion" : "Ya no puedo asistir",
        })
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "cancelada")
        self.assertEqual(self.reserva.motivo_cancelacion, "Ya no puedo asistir")

    def test_cancelacion_con_codigo_incorrecto_no_cancela(self):
        self.client.post("/consultorio/cancelar_hora", {
            "action"    : "seleccionar",
            "reserva_id": self.reserva.id,
        })
        self.client.post("/consultorio/cancelar_hora", {
            "action"             : "confirmar",
            "confirmar_reserva_id": self.reserva.id,
            "codigo"             : "000000",
            "motivo_cancelacion" : "",
        })
        self.reserva.refresh_from_db()
        self.assertNotEqual(self.reserva.estado, "cancelada")

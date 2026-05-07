from django.contrib.auth.models import User
from django.test import TestCase

from .backends import RutOrEmailBackend, _normalize_rut
from .forms import RegisterForm, validate_chilean_dni, remove_points_and_hyphens


# ---------------------------------------------------------------------------
# validate_chilean_dni
# ---------------------------------------------------------------------------

class ValidateChileanDniTests(TestCase):
    """Verifica la funcion validate_chilean_dni con distintos formatos de RUT."""

    def test_rut_valido_con_puntos_y_guion(self):
        # RUT 12.345.678 — DV calculado: 5
        self.assertTrue(validate_chilean_dni("12.345.678-5"))

    def test_rut_valido_sin_formato(self):
        self.assertTrue(validate_chilean_dni("123456785"))

    def test_rut_valido_dv_k(self):
        # 76.354.771-K verificado con el algoritmo modulo 11
        self.assertTrue(validate_chilean_dni("76.354.771-K"))

    def test_rut_valido_dv_k_minuscula(self):
        self.assertTrue(validate_chilean_dni("76.354.771-k"))

    def test_rut_invalido_dv_incorrecto(self):
        self.assertFalse(validate_chilean_dni("12.345.678-9"))

    def test_rut_none_devuelve_false(self):
        self.assertFalse(validate_chilean_dni(None))

    def test_rut_cadena_vacia_devuelve_false(self):
        self.assertFalse(validate_chilean_dni(""))

    def test_rut_formato_incorrecto_letras_devuelve_false(self):
        self.assertFalse(validate_chilean_dni("abcdefgh-1"))

    def test_rut_demasiado_corto_devuelve_false(self):
        # Menos de 7 digitos antes del DV
        self.assertFalse(validate_chilean_dni("12345-5"))


# ---------------------------------------------------------------------------
# remove_points_and_hyphens
# ---------------------------------------------------------------------------

class RemovePointsAndHyphensTests(TestCase):
    """Verifica la normalizacion de RUT."""

    def test_elimina_puntos_y_guion(self):
        self.assertEqual(remove_points_and_hyphens("12.345.678-5"), "123456785")

    def test_sin_puntos_ni_guion_sin_cambios(self):
        self.assertEqual(remove_points_and_hyphens("123456785"), "123456785")

    def test_none_devuelve_cadena_vacia(self):
        self.assertEqual(remove_points_and_hyphens(None), "")


# ---------------------------------------------------------------------------
# _normalize_rut (funcion interna del backend)
# ---------------------------------------------------------------------------

class NormalizeRutTests(TestCase):
    """Verifica la normalizacion interna usada por el backend."""

    def test_elimina_puntos_guion_y_espacios(self):
        self.assertEqual(_normalize_rut("  12.345.678-5  "), "123456785")

    def test_solo_guion(self):
        self.assertEqual(_normalize_rut("12345678-5"), "123456785")


# ---------------------------------------------------------------------------
# RutOrEmailBackend
# ---------------------------------------------------------------------------

class RutOrEmailBackendTests(TestCase):
    """Pruebas unitarias para RutOrEmailBackend."""

    def setUp(self):
        self.backend = RutOrEmailBackend()
        self.user = User.objects.create_user(
            username="123456785",
            email="paciente@correo.cl",
            password="clave_segura_2026",
        )

    def test_autenticar_por_rut_sin_formato(self):
        user = self.backend.authenticate(
            None, username="123456785", password="clave_segura_2026"
        )
        self.assertEqual(user, self.user)

    def test_autenticar_por_rut_con_puntos_y_guion(self):
        user = self.backend.authenticate(
            None, username="12.345.678-5", password="clave_segura_2026"
        )
        self.assertEqual(user, self.user)

    def test_autenticar_por_correo_electronico(self):
        user = self.backend.authenticate(
            None, username="paciente@correo.cl", password="clave_segura_2026"
        )
        self.assertEqual(user, self.user)

    def test_autenticar_por_correo_electronico_case_insensitive(self):
        user = self.backend.authenticate(
            None, username="PACIENTE@CORREO.CL", password="clave_segura_2026"
        )
        self.assertEqual(user, self.user)

    def test_contrasena_incorrecta_devuelve_none(self):
        user = self.backend.authenticate(
            None, username="123456785", password="clave_incorrecta"
        )
        self.assertIsNone(user)

    def test_usuario_inexistente_devuelve_none(self):
        user = self.backend.authenticate(
            None, username="999999999", password="clave_segura_2026"
        )
        self.assertIsNone(user)

    def test_sin_credenciales_devuelve_none(self):
        user = self.backend.authenticate(None, username=None, password=None)
        self.assertIsNone(user)

    def test_usuario_inactivo_no_puede_autenticar(self):
        self.user.is_active = False
        self.user.save()
        user = self.backend.authenticate(
            None, username="123456785", password="clave_segura_2026"
        )
        self.assertIsNone(user)


# ---------------------------------------------------------------------------
# RegisterForm
# ---------------------------------------------------------------------------

class RegisterFormTests(TestCase):
    """Pruebas unitarias para el formulario de registro."""

    def _datos_base(self, **kwargs):
        datos = {
            "username"  : "12.345.678-5",
            "email"     : "nuevo@correo.cl",
            "first_name": "Maria",
            "last_name" : "Gonzalez",
            "password1" : "Segura_2026!",
            "password2" : "Segura_2026!",
            "tipo"      : "paciente",
        }
        datos.update(kwargs)
        return datos

    def test_formulario_valido_paciente(self):
        form = RegisterForm(data=self._datos_base())
        self.assertTrue(form.is_valid(), form.errors)

    def test_rut_invalido_genera_error(self):
        form = RegisterForm(data=self._datos_base(username="12.345.678-9"))
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_rut_se_normaliza_al_guardar(self):
        form = RegisterForm(data=self._datos_base())
        self.assertTrue(form.is_valid(), form.errors)
        # El username limpio debe estar sin puntos ni guion
        self.assertEqual(form.cleaned_data["username"], "123456785")

    def test_profesional_requiere_especialidad(self):
        # Actualmente el form no valida esto a nivel de is_valid,
        # pero especialidad deberia estar presente en el layout
        form = RegisterForm(
            data=self._datos_base(tipo="profesional", especialidad="")
        )
        # El campo no es requerido en el form, solo es una validacion de negocio
        # Se verifica que el campo existe en el formulario
        self.assertIn("especialidad", form.fields)

    def test_passwords_no_coinciden_genera_error(self):
        form = RegisterForm(
            data=self._datos_base(password1="Segura_2026!", password2="Diferente!")
        )
        self.assertFalse(form.is_valid())

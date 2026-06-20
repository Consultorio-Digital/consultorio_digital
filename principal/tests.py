from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class PrincipalViewTests(TestCase):
    """Pruebas para la vista principal (landing e inicio autenticado)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username   = "222222226",
            password   = "clave_prueba_2026",
            first_name = "Juan",
            last_name  = "Soto",
        )

    def test_landing_redirige_sin_login(self):
        # Un usuario anonimo en / es redirigido al login (302), comportamiento
        # intencional: el home solo se muestra a usuarios autenticados.
        response = self.client.get(reverse("principal:principal"))
        self.assertEqual(response.status_code, 302)

    def test_landing_redirige_a_login(self):
        # El redirect debe apuntar a la pagina de login.
        response = self.client.get(reverse("principal:principal"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("login"))

    def test_inicio_autenticado_retorna_200(self):
        self.client.login(username="222222226", password="clave_prueba_2026")
        response = self.client.get(reverse("principal:principal"))
        self.assertEqual(response.status_code, 200)

    def test_inicio_autenticado_muestra_nombre_usuario(self):
        self.client.login(username="222222226", password="clave_prueba_2026")
        response = self.client.get(reverse("principal:principal"))
        self.assertContains(response, "Juan")

    def test_inicio_autenticado_muestra_tabla_proximas_citas(self):
        self.client.login(username="222222226", password="clave_prueba_2026")
        response = self.client.get(reverse("principal:principal"))
        content  = response.content.decode()
        self.assertIn("Próximas citas", content)

    def test_context_reservas_presente_para_usuario_autenticado(self):
        self.client.login(username="222222226", password="clave_prueba_2026")
        response = self.client.get(reverse("principal:principal"))
        # La vista debe pasar la variable 'reservas' al template
        self.assertIn("reservas", response.context)

    def test_reservas_vacias_muestra_mensaje_sin_citas(self):
        self.client.login(username="222222226", password="clave_prueba_2026")
        response = self.client.get(reverse("principal:principal"))
        self.assertContains(response, "No tienes citas")

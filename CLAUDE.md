# CLAUDE.md — Contexto del proyecto Consultorio Digital

## Descripción
Sistema Django de gestión de horas médicas para consultorios
de atención primaria en Chile. Proyecto académico ICI-513, UV.

## Stack
- Python 3.12 + Django 5.1 + Poetry
- PostgreSQL 16 en Docker, SQLite como fallback local
- Bootstrap 5.3 + Django Templates (sin JS framework)
- docker-compose con servicios: web + db

## Apps Django
- principal: vistas home, panel_admin, panel_doctor, ayuda
- registro: registro de usuarios, autenticación por RUT o email
- consultorio: modelos del dominio + vistas de reservas + AJAX

## Modelo de datos clave
- auth.User (autenticación) + consultorio.Usuario (dominio)
  vinculados por RUT normalizado (sin puntos ni guión)
- Profesional → OneToOne → Usuario, FK → Consultorio
- Paciente → OneToOne → Usuario
- Administrador → OneToOne → Usuario
- Reserva → FK Paciente, Profesional, Consultorio
- Disponibilidad → FK Profesional (unique: profesional+fecha+hora_inicio)

## Roles y acceso
- Administrador: is_staff=True, redirige a principal:panel_admin
- Profesional: redirige a principal:panel_doctor
- Paciente: redirige a principal:principal (home)
- La detección de rol ocurre en principal/views.py home()

## Comandos de gestión
- cargar_consultorios: carga utils/data/geodata.json en BD
- poblar_datos: seed idempotente (6 prof en Viña, 10 pac, 20 reservas)
- crear_admin: crea/actualiza admin (idempotente, corre en cada up)

## Arranque Docker
cp .env.docker .env && docker compose up --build
# Primera vez además:
docker compose exec web python manage.py cargar_consultorios
docker compose exec web python manage.py poblar_datos

## Credenciales de prueba
- Admin: 12345678-9 / admin123
- Profesionales: 11111111-1 al 55555555-5 / prof123
- María González (Nueva Aurora, Viña): 99999999-9 NO tiene RUT válido,
  fue creada por management command. Usar otros profesionales.
- Pacientes: 66666666-6 en adelante / pac123

## Convenciones del proyecto
- Todo en español (templates, mensajes, labels)
- IDs de CSS institucionales: #1a3a5c (azul oscuro), #f0f4f8 (fondo)
- Badges de estado: partial en templates/_badge_estado.html
- Modal historial paciente: partial en templates/_modal_historial.html
- Migraciones: NO incluir desfases preexistentes (solo cambios propios)
- El campo auth.User.username almacena el RUT normalizado
- STATICFILES_DIRS = [BASE_DIR / "static"]
- TIME_ZONE = 'America/Santiago', LANGUAGE_CODE = 'es-cl'

## Archivos importantes
- salud_publica_digital/settings.py: config central
- consultorio/models.py: TODOS los modelos del dominio
- principal/views.py: home() detecta rol y redirige
- consultorio/views.py: reservas, slots AJAX, historial
- registro/backends.py: autenticación por RUT o email
- templates/base.html: layout global + navbar
- static/css/navbar.css: estilos globales + transiciones
- static/css/principal.css: estilos de vistas principales

## Hallazgos resueltos (no reabrir)
- Usuario.direccion era EmailField → corregido a CharField (migración 0008)
- certifica max_length=3 desbordaba en PostgreSQL → corregido (migración 0009)
- panel_doctor redirigía a URL inexistente → corregido
- STATICFILES_DIRS faltaba → corregido
- datos address/phone/birthdate no persistían en registro → corregido

## Deuda técnica conocida
- Código de cancelación se muestra en pantalla (debería ir por email)
- Se permiten reservas en fechas pasadas (intencional para pruebas)
- María González tiene RUT matemáticamente inválido (99999999-9)
- mis_horas.css es CSS muerto (ningún template lo enlaza)
- queries/data.json (~29MB) versionado innecesariamente

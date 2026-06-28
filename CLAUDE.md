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
  - estados: pendiente, confirmada, completada, seguimiento, cancelada,
    no_asistio, sin_gestionar
  - Reserva.expirar_pendientes(): classmethod idempotente que marca como
    'sin_gestionar' las 'pendiente' cuya fecha_reserva ya pasó (las
    'confirmada' vencidas NO se tocan, las cierra el doctor)
- Disponibilidad → FK Profesional (unique: profesional+fecha+hora_inicio)

## Roles y acceso
- Administrador: is_staff=True (NO superuser), redirige a principal:panel_admin
- Profesional: redirige a principal:panel_doctor
- Paciente: redirige a principal:principal (home)
- La detección de rol ocurre en principal/views.py home()
- El admin pertenece al grupo "Administradores" (permisos acotados):
  CRUD de modelos de dominio + ver/editar auth.User. Da acceso al /admin/
  de Django sin ser superusuario. Se asigna en crear_admin.

## Capacidades del administrador
- Panel custom (/panel_admin/), acciones en principal/views.py:
  - admin_actualizar_reserva: cambia estado de cualquier reserva (POST,
    _es_admin, 403/404/400). Si estado='cancelada' guarda motivo.
  - admin_toggle_cuenta: activa/desactiva auth.User por RUT. No permite
    que el admin se desactive a sí mismo.
  - admin_exportar_reservas: exporta TODAS las reservas a CSV (BOM UTF-8).
- Django /admin/: CRUD acotado vía grupo de permisos (enlace en el panel).

## Comandos de gestión
- cargar_consultorios: carga utils/data/geodata.json en BD
- poblar_datos: seed idempotente (6 prof en Viña, 10 pac, 20 reservas)
- crear_admin: crea/actualiza admin (idempotente, corre en cada up);
  también configura el grupo "Administradores" y se lo asigna al usuario
- marcar_sin_gestionar: marca pendientes vencidas como 'sin_gestionar'
  (idempotente; para correr por cron). Los paneles ya lo disparan en modo
  lazy vía Reserva.expirar_pendientes() al cargar (home/panel_doctor/panel_admin)

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
- Navbar centralizado en base.html según rol (NO usar {% block navbar %}
  por template; se eliminaron). El link activo se marca con
  request.resolver_match.url_name
- Feedback al usuario vía django.contrib.messages (NO session); se renderiza
  globalmente en base.html. settings.MESSAGE_TAGS mapea ERROR → 'danger'
- Tooltips: data-bs-toggle="tooltip" + data-bs-title (no title nativo en el
  mismo elemento, para evitar tooltip doble); init global en base.html
- Coordenadas en URLs (Maps): usar |stringformat:"f" para forzar punto
  decimal (el locale es-cl renderiza coma y rompe el link)
- Completar consulta (panel doctor): el modal Completar incluye un check
  opcional "Agendar seguimiento" + fecha; si se marca, el JS cambia
  nuevo_estado a 'seguimiento' (Completado → Seguimiento en un solo paso)
- Calendario de disponibilidad: tab "Disponibilidades" del panel doctor
  renderiza un calendario mensual vanilla JS (sin libs). Datos vía
  disponibilidades_cal → json_script "disp-data". Estilos .cal-* en
  principal.css. Agregar disponibilidad sigue en el tab "Gestionar"
- Registro dinámico: el selector de tipo es un toggle de dos botones
  (#btn-paciente / #btn-profesional) que llaman a setTipo(tipo) (función
  JS global). setTipo alterna las clases .active-toggle/.inactive-toggle,
  muestra/oculta #div-profesional con classList.toggle('d-none') y escribe
  el valor en el hidden name="tipo" id="id_tipo" (los botones NO son campos,
  el hidden es el que viaja en el POST). Profesional → especialidad
  obligatoria (cliente: required JS; servidor: RegisterForm.clean()) +
  cascada región→comuna→consultorio opcional (asigna Profesional.consultorio
  en registro/views.py). tipo/especialidad/consultorio se renderizan a mano
  en registro.html; el resto vía {% crispy form %} (TAG, no el filtro
  |crispy) con helper.render_unmentioned_fields=False para que crispy NO
  repinte esos 3 campos. Orden: toggle → especialidad → recinto → RUT →
  correo → nombre → apellido → dirección → teléfono → fecha nac → claves
- obtener_comunas / obtener_consultorios: geodata pública SIN login (la
  usa la cascada del registro anónimo); el resto de endpoints sí exige login
- Recuperación de contraseña: flujo estándar de django.contrib.auth
  (incluido en urls.py vía include('django.contrib.auth.urls')). Templates
  propios en registro/templates/registration/ (password_reset_form.html
  —OJO: NO password_reset.html—, _done, _confirm, _complete), todos con el
  estilo de la card de login (max-width 460px). El cuerpo del correo usa el
  template por defecto de contrib.admin. Link "¿Olvidaste tu contraseña?"
  en login.html. EMAIL_BACKEND = console en settings (el correo se imprime
  en consola en desarrollo)
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
- consultorio/context_processors.py: rol_usuario expone es_admin/
  es_profesional/es_paciente a todos los templates (lo usa el navbar)
- templates/base.html: layout global + navbar role-aware + bloque de
  mensajes (django messages) + init global de tooltips Bootstrap
- static/css/navbar.css: tokens de diseño (escala tipográfica y de
  espaciado) + estilos globales (navbar, cards, botones, tablas, forms)
- static/css/principal.css: estilos de vistas (tablas, badges, tabs,
  stats, accordion de ayuda)
- static/css/login.css: estilos de login/registro
  (NO existen form.css, mis_horas.css ni consultorio.css — eliminados)

## Sistema de diseño (CSS)
- Variables en :root de navbar.css (cargado global por base.html):
  - Tipografía: --font-size-xs/sm/base/md/lg/xl, --font-weight-*,
    --line-height-tight/base/relaxed
  - Espaciado: --space-xs/sm/md/lg/xl/2xl
- Títulos de página: <h1> (sin .h3) → font-size-xl + bold (regla global)
- Padding de cards unificado vía .card-body (var(--space-lg)); NO usar
  utilidades p-4/p-md-5 en card-body
- Padding de celdas de tabla vía variables Bootstrap en .table
- Los CSS llevan banners de sección: /* ═══ NAVBAR ═══ */, CARDS, etc.

## Hallazgos resueltos (no reabrir)
- Usuario.direccion era EmailField → corregido a CharField (migración 0008)
- certifica max_length=3 desbordaba en PostgreSQL → corregido (migración 0009)
- panel_doctor redirigía a URL inexistente → corregido
- STATICFILES_DIRS faltaba → corregido
- datos address/phone/birthdate no persistían en registro → corregido
- CSS muerto (form.css, mis_horas.css, consultorio.css) → eliminado;
  estilos consolidados y tokenizados en navbar.css + principal.css
- navbar duplicado en 9 templates → centralizado en base.html vía
  context processor rol_usuario
- confirmación/cancelación de reservas usaban session → migradas a
  django messages (render global en base.html)
- link de Google Maps salía con coma decimal (locale es-cl) → corregido
  con |stringformat:"f"

## Deuda técnica conocida
- Código de cancelación se muestra en pantalla (debería ir por email)
- Se permiten reservas en fechas pasadas (intencional para pruebas)
- María González tiene RUT matemáticamente inválido (99999999-9)
- queries/data.json (~29MB) versionado innecesariamente

## Testing

### Stack de tests
- pytest + pytest-django + pytest-cov (instalados en grupo dev)
- Tests unittest legacy en cada app (tests.py): ~79 tests
- Tests pytest nuevos en tests/: 47 tests (incluye test_admin_acciones.py,
  test_nuevas_features.py: seguimiento, expiración, calendario, registro;
  y en test_registro.py: toggle setTipo + flujo de recuperación de clave)
- Total: 126 tests

### Correr tests
poetry run pytest -v
poetry run pytest --cov=principal --cov=registro --cov=consultorio --cov-report=term-missing

### Fixtures disponibles (tests/conftest.py)
- cliente: django.test.Client()
- admin_user: RUT 12345678-9, is_staff=True
- profesional_user: RUT 11111111-1, Medicina General
- paciente_user: RUT 66666666-6
- consultorio: objectid=9999, Viña del Mar

### Cobertura por módulo
- registro/backends.py: 100%
- consultorio/models.py: 98%
- registro/forms.py: 95%
- registro/views.py: 93%
- consultorio/views.py: 64% (endpoints AJAX nuevos sin cubrir)
- principal/views.py: 75% (acciones admin testeadas; falta render
  completo de panel_doctor/panel_admin)

### Deuda de tests conocida
- panel_doctor y panel_admin: solo se testea control de acceso,
  no el render completo con datos
- agregar_disponibilidad y cambiar_consultorio sin tests
- endpoints AJAX parcialmente cubiertos

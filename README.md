# Consultorio Digital

Sistema web de gestión de horas médicas para consultorios de
atención primaria en Chile. Desarrollado para el curso ICI-513,
Ingeniería Civil en Informática — Universidad de Valparaíso.

## Stack tecnológico
- Backend: Python 3.12 + Django 5.1
- Frontend: Django Templates + Bootstrap 5.3
- Base de datos: PostgreSQL 16 (SQLite en desarrollo sin Docker)
- Contenedores: Docker + Docker Compose
- Dependencias: Poetry

## Roles del sistema
| Rol | Acceso | Credenciales de prueba |
|-----|--------|----------------------|
| Administrador | /panel_admin/ | 12345678-9 / admin123 |
| Profesional | /panel_doctor/ | 11111111-1 / prof123 |
| Paciente | / | Registrarse en /registro/ |

## Levantar con Docker (recomendado)
```bash
cp .env.docker .env
docker compose up --build
```

Primera vez — cargar datos:
```bash
docker compose exec web python manage.py cargar_consultorios
docker compose exec web python manage.py poblar_datos
```
El administrador se crea automáticamente en cada arranque.

## Levantar sin Docker
```bash
poetry install
poetry run python manage.py migrate
poetry run python manage.py cargar_consultorios
poetry run python manage.py poblar_datos
poetry run python manage.py runserver
```

## Comandos de gestión
| Comando | Descripción |
|---------|-------------|
| cargar_consultorios | Carga 2.560 consultorios reales del MINSAL |
| poblar_datos | Genera 6 profesionales, 10 pacientes, 20 reservas de prueba en Viña del Mar |
| crear_admin | Crea o actualiza el administrador del sistema |

## Tests y Cobertura

### Correr todos los tests
```bash
poetry run pytest -v
```

### Correr con reporte de cobertura
```bash
poetry run pytest --cov=principal --cov=registro --cov=consultorio \
  --cov-report=term-missing
```

### Resultado actual
- 96 tests en verde (79 unittest + 17 pytest)
- Cobertura global: 77%
- registro/backends.py: 100%
- consultorio/models.py: 98%
- registro/forms.py: 95%

### Herramientas de testing
| Herramienta | Versión | Uso |
|-------------|---------|-----|
| pytest | 9.1 | Ejecución de tests |
| pytest-django | 4.12 | Integración con Django |
| pytest-cov | 7.1 | Reporte de cobertura |

## Estructura del proyecto
```
GPI/
├── principal/      # App: home, panel paciente, panel admin, panel doctor
├── registro/       # App: registro de usuarios y autenticación
├── consultorio/    # App: núcleo del dominio (reservas, disponibilidades)
├── templates/      # Templates globales (base.html, ayuda.html)
├── static/         # CSS e imágenes
├── utils/          # geodata.json con consultorios del MINSAL
├── docs/           # Documentación académica y técnica
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## Variables de entorno
Ver .env.example para la lista completa de variables requeridas.

## Tests
Ver la sección [Tests y Cobertura](#tests-y-cobertura).

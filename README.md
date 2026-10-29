# Pataporte

Aplicación web para la gestión del historial médico de mascotas. Permite a tutores registrar sus animales, y a organizaciones veterinarias llevar el registro de consultas, tratamientos y vacunas con certificación digital.

Proyecto desarrollado para Ingeniería de Software II.

---

## Tabla de contenido

- [Tecnologías](#tecnologías)
- [Arquitectura](#arquitectura)
- [Funcionalidades](#funcionalidades)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación y ejecución](#instalación-y-ejecución)
- [Variables de entorno](#variables-de-entorno)
- [Documentación de la API](#documentación-de-la-api)

---

## Tecnologías

**Backend**

- Python 3.11 + FastAPI
- PostgreSQL 15 con SQLAlchemy 2 (ORM) y Alembic (migraciones)
- Autenticación JWT (PyJWT + bcrypt)
- Envío de correos (verificación y recuperación de contraseña)

**Frontend**

- HTML5 + CSS + JavaScript vanilla
- Servido por Nginx

**Infraestructura**

- Docker y Docker Compose

---

## Arquitectura

![Arquitectura del sistema](/frontend/assets/pataporte_architecture.jpg)

---

## Funcionalidades

- Registro y autenticación de tutores y organizaciones veterinarias con verificación de correo
- Recuperación de contraseña por correo
- Gestión de mascotas: crear, ver y editar perfil (nombre, fecha de nacimiento, sexo, especie, raza, foto)
- Registro de consultas veterinarias con diagnóstico y notas de tratamiento
- Seguimiento de tratamientos activos con fechas de inicio y fin
- Esquema de vacunación con tipos predefinidos (Antirrábica, Moquillo, Parvovirus, Triple Felina)
- Certificados digitales de vacunación con hash de verificación, estados y flujo de revisión
- Historial médico unificado con consultas y tratamientos

---

## Estructura del proyecto

```
pataporte/
├── backend/
│   ├── config/         # Configuración de base de datos y settings
│   ├── routers/        # Endpoints de la API agrupados por dominio
│   ├── schemas/        # Modelos Pydantic (validación de entrada/salida)
│   ├── services/       # Lógica de negocio
│   ├── utils/          # Utilidades compartidas
│   ├── main.py         # Inicialización de la app FastAPI
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── pages/          # Páginas HTML
│   ├── js/             # Módulos JavaScript
│   ├── index.html
│   └── Dockerfile
├── localstack/        # Init de LocalStack (S3 + SQS locales)
├── .env.example        # Plantilla de variables de entorno
└── docker-compose.yml
```

---

## Instalación y ejecución

### Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) y Docker Compose instalados
- Crear archivo con las variables de entorno, asegurarse de que el nombre incluya el punto: ".env"

### Pasos

1. Clonar el repositorio:

   ```bash
   git clone <url-del-repositorio>
   cd pataporte
   ```

2. Crear el archivo de entorno a partir de la plantilla:

   ```bash
   cp .env.example .env
   ```

3. Editar `.env` con los valores correspondientes (ver sección [Variables de entorno](#variables-de-entorno)).

4. Levantar los servicios (LocalStack hace de S3/SQS; el servicio `init-db` crea tablas y seed antes del backend):

   ```bash
   docker compose up --build
   ```

   Para re-inicializar la base a mano: `docker compose run --rm init-db` (equivale a `python -m scripts.init_db`).

5. Tests del backend:

   ```bash
   cd backend && pip install -r requirements-dev.txt && pytest
   ```

Una vez levantados:

| Servicio      | URL                        |
| ------------- | -------------------------- |
| Frontend      | http://localhost           |
| API           | http://localhost/api       |
| API Docs      | http://localhost/api/docs  |
| Base de datos | localhost:5432             |

---

## Variables de entorno

| Variable                      | Descripción                                       |
| ----------------------------- | ------------------------------------------------- |
| `DB_USER`                     | Usuario de PostgreSQL                             |
| `DB_PASSWORD`                 | Contraseña de PostgreSQL                          |
| `DB_NAME`                     | Nombre de la base de datos                        |
| `DATABASE_URL`                | URL de conexión completa para FastAPI             |
| `SECRET_KEY`                  | Clave secreta para firmar tokens JWT              |
| `ALGORITHM`                   | Algoritmo JWT (por defecto `HS256`)               |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración del token de acceso en minutos           |
| `MAIL_USERNAME`               | Usuario del correo para envío de emails           |
| `MAIL_PASSWORD`               | Contraseña de aplicación del correo               |
| `MAIL_FROM`                   | Dirección remitente de los correos                |
| `DB_HOST` / `DB_PORT`         | Host y puerto de PostgreSQL (si no hay `DATABASE_URL`) |
| `CORS_ORIGINS`                | Orígenes permitidos, separados por coma           |
| `SMTP_HOST` / `SMTP_PORT`     | Servidor SMTP (por defecto `smtp.gmail.com:587`)  |
| `AWS_REGION`                  | Región AWS (por defecto `us-east-1`)              |
| `UPLOADS_BUCKET`              | Bucket S3 para fotos y PDFs                       |
| `QUEUE_URL`                   | Cola SQS que consume el worker                    |
| `EVENT_BUS_NAME`              | Opcional: bus de EventBridge para publicar eventos |
| `LOG_LEVEL`                   | Nivel de logs (por defecto `INFO`)                |
| `ENVIRONMENT`                 | Entorno de ejecución (`development`/`production`) |

---

## Documentación de la API

FastAPI genera documentación interactiva automáticamente:

- **Swagger UI**: http://localhost/api/docs
- **ReDoc**: http://localhost/api/redoc

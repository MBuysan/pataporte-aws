# Primer hito: entorno local, pruebas y base de infraestructura

Preparado el 25 de octubre de 2026. La guía completa está en
[la página interactiva](guia-despliegue-aws.html).

## Qué se implementó

- PostgreSQL, RabbitMQ, FastAPI, worker, Nginx y Mailpit en Compose.
- Configuración local generada con claves nuevas; el generador conserva un .env existente.
- Web y correo accesibles únicamente desde localhost. PostgreSQL y AMQP no se publican al host.
- Solicitudes del navegador por /api en el mismo origen: Nginx quita ese prefijo antes de FastAPI.
- Correos en Mailpit: registro, recuperación y PDF pueden probarse sin Gmail.
- Autenticación común con cuenta activa, controles de propiedad para tutores y rol veterinario para escritura clínica.
- Eliminación del código universal de verificación, corrección del correo de recuperación y de errores silenciosos del worker.
- Health checks separados, sin autoreload en la imagen.
- CI con construcción de imágenes, seis pruebas de mensajería, diez de integración y validación de CloudFormation.
- Plantilla de red en dos AZ; no se ejecutó un despliegue AWS.

## Cómo iniciarlo

Desde la raíz del repositorio, con Docker iniciado:

```bash
python3 scripts/init_local.py
docker compose up -d --build
python3 scripts/check_local.py
docker compose exec -T backend python -m unittest discover -s tests -v
```

El primer comando no sobrescribe una configuración existente. Si tenés un .env antiguo,
revisá los nuevos campos de SMTP y RabbitMQ antes de iniciar. Si cambiás credenciales
de PostgreSQL/RabbitMQ después de crear sus volúmenes, esas credenciales deben
actualizarse también en el servicio; editar el .env no reinicializa los datos.

| Recurso | Dirección |
|---|---|
| PATAPORTE | http://localhost:8085 |
| Buzón de pruebas | http://localhost:8025 |
| Swagger | http://localhost:8000/docs |
| Estado de la API por Nginx | http://localhost:8085/api/health/ready |
| RabbitMQ Management | http://localhost:15672 |

Registrá una cuenta ficticia, buscá su código en Mailpit y verificala en la web.
Las credenciales de RabbitMQ se generan en el .env local. No hay una cuenta de
administrador de PATAPORTE creada por este cambio.

Cada ejecución de los ensayos agrega usuarios, mascotas y correos ficticios con
identificadores nuevos. No ejecutarlos contra un entorno con usuarios reales.

Para ver logs y detener sin borrar los datos:

```bash
docker compose logs --tail=100 backend worker
docker compose down
```

## CloudFormation: primera entrega para infraestructura

El archivo infra/network.yaml define VPC, seis subredes, tablas de rutas,
Internet Gateway, SG de ALB/API/workers/RDS y Gateway Endpoints S3/DynamoDB.
Los Outputs incluyen IDs exportados con el nombre del stack.

NatMode acepta none, single o per-az. El valor predeterminado none no crea NAT
ni salida general a Internet desde las subredes privadas. Antes de desplegar ECS
habrá que elegir salida y conectividad para ECR, ECS, logs y secretos.
Las subredes de datos no reciben una ruta por NAT.

Validación local con la misma versión utilizada en CI:

```bash
python3 -m pip install cfn-lint==1.20.0
cfn-lint infra/network.yaml
```

El despliegue debe esperar a que se confirme la cuenta, región, permisos y saldo
de Academy. No hace falta configurar credenciales AWS para ejecutar CI.

## Reparto inmediato

| Persona | Siguiente entrega |
|---|---|
| A: plataforma y datos | Confirmar cuenta/roles/cuotas y revisar red; luego diseñar stack RDS. |
| B: aplicación y eventos | Revisar política clínica y agregar migraciones; preparar el contrato outbox/SQS. |
| C: entrega y operación | Subir el workflow mediante PR y comprobar el primer run remoto; preparar artefactos y despliegue. |

La identidad que puede entrar al laboratorio no determina la autoría del código:
los tres pueden aportar PR, revisiones y ensayos desde el mismo repositorio.

## Qué se comprobó y qué queda pendiente

Las pruebas de integración usan HTTP real por Nginx, PostgreSQL, RabbitMQ, worker
y Mailpit. Verifican código real de correo y rechazo del bypass, login, permisos,
consulta con dosis, verificación de pataporte, adjunto PDF y recuperación de un solo uso.
Las pruebas de mensajería comprueban ACK/NACK, selección de plantilla y propagación
de fallos SMTP. CloudFormation se valida con cfn-lint.

El archivo de workflow está preparado; un resultado en GitHub requiere publicar
los cambios y ejecutar Actions. No se hizo push, no se creó infraestructura AWS y
no se validaron permisos de una cuenta Academy.

Este es un hito de desarrollo local, no una certificación de seguridad de producción.
Pendientes relevantes:

- Migraciones Alembic; todavía se utiliza create_all/seed al arrancar.
- Transactional outbox, SQS/Lambda/DynamoDB y reintentos idempotentes.
- En RabbitMQ, un fallo va a emails.failed para inspección, sin redrive automático.
- Fotos locales en volumen; su sustitución por S3 privado y permisos de descarga.
- Política clínica: actualmente un veterinario activo puede atender mascotas de la
  plataforma. No hay asignación ni validación profesional externa.
- La actualización del perfil del tutor continúa pendiente en el código existente.
- Revisión de dependencias, límites de carga, rate limiting y hardening del contenedor.

La credencial de correo se quitó de .env_example. Su dueño debe revocarla si seguía
vigente: eliminarla del archivo no la retira del historial Git ni del proveedor.

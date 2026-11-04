# Primer hito: entorno local, pruebas y base de infraestructura

## Estado actual — 4 de noviembre de 2026

La migración AWS `0003_transactional_outbox` terminó en cero, con 16 tablas, cinco vacunas, TLS y permisos SQL limitados. La imagen nueva de API quedó aplicada en compute; falta verificación final independiente. Async está desplegado y comprobado mediante SQS → Lambda → DynamoDB/S3 y repetición del evento sin duplicar objeto; el consumidor volvió a quedar pausado. La copia privada de restauración está disponible con aislamiento aprobado, todavía sin comparación SQL. CloudFront quedó en rollback; falta revisar la causa con credenciales renovadas.

Pasaron 61 pruebas locales y seis plantillas. La carga local completó 80 solicitudes autenticadas sin errores, p95 29,506 ms; no es una prueba de AWS. Ver [bitácora](bitacora.html). Faltan renovar sesión Academy vencida, comprobar saldo, cerrar frontend/SMTP/dominio/GitHub y completar los ensayos remotos.

## Última verificación cloud — 27 de octubre de 2026

ECR, NAT, ECS/ALB y migración real de RDS están ejecutados. Hay dos réplicas saludables en dos AZ, con imagen fijada por digest y cuenta SQL DML separada. Se verificaron red (13/13), RDS (16/16), TLS real, permisos SQL, salud HTTP y reemplazo automático de una tarea. Las secciones fechadas 26/10 documentan el estado histórico; los planes pendientes de entonces ya se aprobaron y aplicaron. La guía HTML tiene los resultados actuales y comandos reproducibles en 9.5/9.6.


Preparado el 25 de octubre de 2026; actualizado el 26 de octubre con red, RDS y Alembic. La guía completa está en
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
- CI con construcción de imágenes, seis pruebas de mensajería, cuatro de configuración/TLS,
  cuatro de migraciones reales, diez de integración y validación de CloudFormation.
- Alembic con esquema inicial y catálogo de vacunas; tarea única de migración antes de iniciar la API.
- Red desplegada con CloudFormation en us-east-1: stack pataporte-dev-network,
  CREATE_COMPLETE y 13/13 comprobaciones de infraestructura aprobadas.
- RDS privado PostgreSQL 15.19 en pataporte-dev-data: CREATE_COMPLETE y 16/16
  comprobaciones de configuración aprobadas; migración SQL en AWS pendiente.

## Cómo iniciarlo

Desde la raíz del repositorio, con Docker iniciado:

```bash
python3 scripts/init_local.py
docker compose up -d --build
python3 scripts/check_local.py
docker compose exec -T backend python -m unittest discover -s tests -v
```

Compose ejecuta primero el servicio migrate. En una base anterior compara el
esquema antes de adoptar Alembic y conserva sus registros. Si no coincide, detiene
el inicio de la API para que se prepare una migración específica. No borrar
volúmenes ni marcar versiones manualmente para saltar esa comprobación.

Para ejecutar también los cuatro ensayos de migración en bases efímeras locales:

```bash
docker compose exec -T -e PATAPORTE_RUN_MIGRATION_TESTS=1 backend python -m unittest discover -s tests -v
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

Red y RDS se desplegaron el 26/10/2026. La aplicación y el cómputo todavía no se
desplegaron. No hace falta configurar credenciales AWS para ejecutar el CI local.

### Comprobación de AWS Academy

Se accedió al curso 182602 y a AWS desde Chrome. Para volver a entrar:
Modules → Launch AWS Academy Learner Lab → Start Lab → esperar Ready → AWS.
La consola abrió en us-east-1 (Virginia). La lectura inicial del panel fue
USD 0,10 usados de USD 50; esa lectura puede retrasarse varias horas.
La sesión del curso dura cuatro horas y los recursos persisten entre sesiones.

Se comprobó la identidad de la cuenta con STS, la existencia de LabRole y las
zonas disponibles. Se usaron las credenciales ya disponibles en CloudShell;
no se descargaron claves ni se agregaron a Git. El instructivo recibido permite
us-east-1/us-west-2 y restringe la creación de roles IAM: reutilizar LabRole y
LabInstanceProfile donde corresponda. Esto no equivale a verificar todos los
permisos de los servicios que faltan desplegar.

Con AWS CLI configurado, ejecutar desde la raíz del repositorio, reemplazando
REGION_DEL_LAB por la región que efectivamente muestre el laboratorio:

```bash
python3 scripts/check_aws.py --region REGION_DEL_LAB
```

Puede agregarse --profile NOMBRE si se usa un perfil dedicado, y
--expected-account ID para rechazar una cuenta distinta de la esperada.
El script consulta STS, valida network.yaml en CloudFormation, comprueba dos AZ,
lista VPC de PATAPORTE, verifica CreateVpc mediante --dry-run y consulta LabRole.
No crea recursos, no configura credenciales y no despliega la plantilla.
Un resultado correcto no garantiza todos los permisos de creación del stack,
cuotas disponibles ni presupuesto: son comprobaciones separadas.

AWS documenta la [validación de plantillas](https://docs.aws.amazon.com/cli/latest/reference/cloudformation/validate-template.html),
la [consulta de identidad](https://docs.aws.amazon.com/cli/latest/reference/sts/get-caller-identity.html)
y la [simulación CreateVpc](https://docs.aws.amazon.com/cli/latest/reference/ec2/create-vpc.html).

### Red desplegada y evidencia

| Elemento | Resultado verificado |
|---|---|
| Stack | pataporte-dev-network |
| Región | us-east-1 |
| Estado | CREATE_COMPLETE |
| VPC | vpc-0b2b42541c3318e52 · 10.20.0.0/16 |
| Zonas | us-east-1a y us-east-1b |
| Subredes | 2 públicas, 2 de aplicación privada y 2 de datos privados |
| Recursos del stack | 27, todos completos |
| NAT / Elastic IP / EC2 / RDS / ALB | No creados en este stack |
| Endpoints | S3 y DynamoDB, tipo Gateway, disponibles en las tablas privadas |
| Comprobaciones | 13 de 13 aprobadas |

Se validó la plantilla en AWS, se creó y revisó el conjunto de cambios
network-inicial-20261026, y se ejecutaron únicamente altas de recursos de red.
La VPC de prácticas existente, 10.0.0.0/16, y el stack de Academy se conservaron.
La plantilla desplegada tiene SHA-256:
066385c0c885fabeb59b9147ab835b0c6f73cd01a598fa008b87c5b1b6391ad7.

Las pruebas consultaron CloudFormation y EC2 para verificar DNS, CIDR, etiquetas,
seis subredes en dos AZ, asignación de IP pública desactivada, rutas públicas al
Internet Gateway, ausencia de ruta general desde app/datos, ausencia de NAT,
endpoints y reglas de SG. Son comprobaciones de configuración; todavía no hay
aplicación ni base desplegadas para probar tráfico de extremo a extremo en AWS.

- [Informe JSON real de verificación](evidencias/network-verification-2026-10-26.json).
- [Captura de CloudFormation en CREATE_COMPLETE](evidencias/network-create-complete-2026-10-26.png).
- [Parámetros de desarrollo reproducibles](../infra/parameters/network-dev.json).

Para repetir las comprobaciones, desde un checkout en CloudShell o con AWS CLI
configurado localmente, reemplazar ID_CUENTA_DEL_LAB por el ID que muestre la
consola. El script rechaza otra cuenta y no modifica recursos:

```bash
python3 scripts/verify_network.py \
  --region us-east-1 \
  --expected-account ID_CUENTA_DEL_LAB \
  --report /tmp/pataporte-network-verification.json
```

El verificador corresponde a esta primera red con NatMode=none. Si se cambia
ese diseño en una entrega posterior, se deben actualizar sus criterios.

### Cómo reproducir el despliegue de red

Estos comandos son para una cuenta/región sin un stack de ese nombre. Ejecutar
desde un checkout del proyecto y comprobar antes la cuenta con STS. En el stack
ya existente, las modificaciones se preparan con --change-set-type UPDATE y un
nombre de conjunto de cambios nuevo; revisar siempre el resultado antes de ejecutar.

```bash
aws sts get-caller-identity --region us-east-1
aws cloudformation validate-template \
  --region us-east-1 \
  --template-body file://infra/network.yaml
aws cloudformation create-change-set \
  --region us-east-1 \
  --stack-name pataporte-dev-network \
  --change-set-name network-inicial \
  --change-set-type CREATE \
  --template-body file://infra/network.yaml \
  --parameters file://infra/parameters/network-dev.json \
  --tags Key=project,Value=pataporte Key=environment,Value=dev Key=managed-by,Value=cloudformation
aws cloudformation wait change-set-create-complete \
  --region us-east-1 \
  --stack-name pataporte-dev-network \
  --change-set-name network-inicial
aws cloudformation describe-change-set \
  --region us-east-1 \
  --stack-name pataporte-dev-network \
  --change-set-name network-inicial
```

Solo después de revisar altas, modificaciones y eliminaciones:

```bash
aws cloudformation execute-change-set \
  --region us-east-1 \
  --stack-name pataporte-dev-network \
  --change-set-name network-inicial
aws cloudformation wait stack-create-complete \
  --region us-east-1 \
  --stack-name pataporte-dev-network
```

En una actualización, el último waiter es stack-update-complete. Estos comandos
usan la sesión actual del operador y no crean roles IAM. La generación inicial
del 26/10 se ejecutó con el SDK ya instalado en CloudShell y estos mismos
parámetros efectivos; la secuencia CLI reproduce esas operaciones.

Mantener NatMode=none conserva el aislamiento inicial. Para ejecutar ECS en
subredes privadas falta resolver salida a ECR, logs, secretos y demás servicios.
Los Gateway Endpoints de S3/DynamoDB no cobran un cargo adicional por el endpoint,
pero eso no implica que cualquier uso futuro de S3/DynamoDB sea gratuito.
[AWS: Gateway Endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html).

## Reparto inmediato

| Persona | Siguiente entrega |
|---|---|
| A: plataforma y datos | Red y RDS desplegados; preparar conectividad de ECS y ejecutar su tarea de migración. |
| B: aplicación y eventos | Migraciones locales listas; revisar política clínica y preparar el contrato outbox/SQS. |
| C: entrega y operación | Subir el workflow mediante PR y comprobar el primer run remoto; preparar artefactos y despliegue. |

La identidad que puede entrar al laboratorio no determina la autoría del código:
los tres pueden aportar PR, revisiones y ensayos desde el mismo repositorio.

## Qué se comprobó y qué queda pendiente

Las pruebas de integración usan HTTP real por Nginx, PostgreSQL, RabbitMQ, worker
y Mailpit. Verifican código real de correo y rechazo del bypass, login, permisos,
consulta con dosis, verificación de pataporte, adjunto PDF y recuperación de un solo uso.
Las pruebas de mensajería comprueban ACK/NACK, selección de plantilla y propagación
de fallos SMTP. CloudFormation se valida con cfn-lint.

El workflow de CI está preparado en el repositorio; su resultado remoto en
GitHub no se comprobó en esta etapa. Sí se crearon y verificaron red y RDS de Academy.
El resto de la arquitectura, sus permisos y el despliegue automatizado por
GitHub Actions siguen pendientes. Las evidencias son del 26/10, no un monitoreo
continuo: repetir la verificación después de cualquier cambio.

Este es un hito de desarrollo local, no una certificación de seguridad de producción.
Pendientes relevantes:

- Ejecutar las migraciones ya implementadas contra RDS mediante una tarea dentro de la VPC.
- Transactional outbox, SQS/Lambda/DynamoDB y reintentos idempotentes.
- En RabbitMQ, un fallo va a emails.failed para inspección, sin redrive automático.
- Fotos locales en volumen; su sustitución por S3 privado y permisos de descarga.
- Política clínica: actualmente un veterinario activo puede atender mascotas de la
  plataforma. No hay asignación ni validación profesional externa.
- La actualización del perfil del tutor continúa pendiente en el código existente.
- Revisión de dependencias, límites de carga, rate limiting y hardening del contenedor.

La credencial de correo se quitó de .env_example. Su dueño debe revocarla si seguía
vigente: eliminarla del archivo no la retira del historial Git ni del proveedor.

## Segundo hito: RDS y migraciones

### Estado real

| Componente | Resultado |
|---|---|
| Stack de datos | pataporte-dev-data · CREATE_COMPLETE |
| Instancia | pataporte-dev-postgres · PostgreSQL 15.19 · db.t3.micro |
| Disco | 20 GB gp2, cifrado con KMS |
| Red | Privada; usa exclusivamente las dos subredes de datos y su SG |
| TLS del servidor | rds.force_ssl=1, parámetro aplicado |
| Credencial | Contraseña maestra generada y administrada por RDS/Secrets Manager |
| Disponibilidad | Single-AZ; EnableMultiAZ parametrizado para la prueba posterior |
| Backups / logs | Retención de uno y siete días respectivamente |
| Borrado | DeletionProtection activo, DeletionPolicy y UpdateReplacePolicy en Snapshot |
| Verificación AWS | 16/16 comprobaciones aprobadas |
| Esquema local | 0002_seed_vaccines, 15 tablas de aplicación y cinco vacunas |
| Pruebas locales | 14 backend/migración/TLS + 10 integración = 24 aprobadas |
| SQL contra RDS | Pendiente de la tarea privada dentro de la VPC |
| Restauración | Pendiente de un ensayo con datos ficticios |

La variante Single-AZ reduce el consumo durante esta etapa del laboratorio.
La arquitectura objetivo conserva la prueba Multi-AZ. El grupo de subredes de
dos AZ permite activarla, aunque la instancia actual se ejecuta en una sola AZ.

- [Informe de configuración real de RDS](evidencias/data-verification-2026-10-26.json).
- [Captura del stack de datos terminado](evidencias/data-create-complete-2026-10-26.png).
- [Versión del esquema local](evidencias/migrations-local-2026-10-26.json).
- [Parámetros efectivos de la base](../infra/parameters/data-dev.json).

### Verificar y reproducir RDS

Se revisó el change set data-inicial-20261026: solo cuatro altas, sin modificar
la red. Los recursos son DB Instance, DB Subnet Group, DB Parameter Group y
Log Group. La credencial administrada la crea RDS; no hay una contraseña en los
parámetros de CloudFormation, el repositorio ni las evidencias.

Para validar la configuración actual, con AWS CLI ya autenticado:

```bash
python3 scripts/verify_data.py \
  --region us-east-1 \
  --expected-account ID_CUENTA_DEL_LAB \
  --report /tmp/pataporte-data-verification.json
```

Ese script consulta metadatos. No pide la contraseña ni ejecuta SQL. Verifica
estado, versión, clase, cifrado, disco, VPC, subredes, SG, puerto, TLS obligatorio,
secreto activo, backups, protección de borrado, logs y configuración de Multi-AZ.

Para recrear el stack en una cuenta sin ese stack, después de desplegar network:

```bash
aws cloudformation validate-template \
  --region us-east-1 --template-body file://infra/data.yaml
aws cloudformation create-change-set \
  --region us-east-1 \
  --stack-name pataporte-dev-data \
  --change-set-name data-inicial \
  --change-set-type CREATE \
  --template-body file://infra/data.yaml \
  --parameters file://infra/parameters/data-dev.json \
  --tags Key=project,Value=pataporte Key=environment,Value=dev Key=managed-by,Value=cloudformation
aws cloudformation wait change-set-create-complete \
  --region us-east-1 --stack-name pataporte-dev-data --change-set-name data-inicial
aws cloudformation describe-change-set \
  --region us-east-1 --stack-name pataporte-dev-data --change-set-name data-inicial
```

Después de revisar el plan:

```bash
aws cloudformation execute-change-set \
  --region us-east-1 --stack-name pataporte-dev-data --change-set-name data-inicial
aws cloudformation wait stack-create-complete \
  --region us-east-1 --stack-name pataporte-dev-data
```

Para una base existente usar UPDATE y otro nombre de change set. Revisar los
reemplazos, snapshots y cualquier cambio de cifrado o de versión antes de ejecutar.
La versión 15.19 se comprobó disponible en us-east-1 al desplegar; volver a
consultar las opciones si se reproduce después o en otra región.

### Cómo funcionan las migraciones

Los modelos están en config/models.py, separados de conexiones y secretos de la
API. Hay dos revisiones congeladas: esquema inicial y catálogo de vacunas.
El comando de despliegue es:

```bash
python -m config.migrate
```

En Compose lo ejecuta el servicio migrate antes de iniciar backend. La API solo
comprueba que el esquema esté en head; ya no ejecuta create_all ni seed al arrancar.
El comando toma un advisory lock de PostgreSQL para rechazar otra migración
simultánea. Una base previa solo se adopta si sus tablas y metadatos coinciden;
si no coinciden, el comando falla sin marcar la versión. El seed respeta filas
que ya tienen el mismo nombre de vacuna y mantiene sus IDs.

Las pruebas crearon bases efímeras distintas de la base de la aplicación. Se
ensayó upgrade desde vacío, repetición sin duplicados, downgrade y nueva
aplicación, conservación de filas previas, rechazo de drift y bloqueo concurrente.
No usar downgrade en una base con datos importantes: el baseline elimina tablas;
el ensayo de reversión se hizo únicamente sobre bases locales temporales.

La conexión admite DATABASE_URL o campos DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD.
Las contraseñas con caracteres especiales se conservan mediante URL.create.
En producción la tarea necesita:

```text
ENVIRONMENT=production
DATABASE_SSLMODE=verify-full
DATABASE_SSLROOTCERT=/app/certs/us-east-1-bundle.pem
```

El bundle público se descargó del [truststore oficial de RDS](https://truststore.pki.rds.amazonaws.com/us-east-1/us-east-1-bundle.pem)
y está incluido en la imagen. La configuración exige una CA existente y
verify-full fuera de desarrollo/pruebas, incluso si DATABASE_URL intenta
especificar otro modo. Las pruebas de TLS son de configuración local; todavía
falta verificar la conexión real al endpoint privado desde la VPC.

### Siguiente paso y operación del laboratorio

Publicar la imagen en ECR, preparar ECS y ejecutar una tarea puntual con
python -m config.migrate, las subredes app, el SG de workers y la credencial
inyectada desde Secrets Manager. Resolver previamente conectividad a ECR, logs
y secretos. Comprobar exit code 0 y la revisión instalada antes de iniciar la API.
La cuenta de aplicación con permisos SQL limitados y el ensayo de restauración
se completan con esa integración. La instancia actual tiene la credencial
maestra administrada; no se afirma aislamiento SQL por usuario todavía.

RDS permanece encendida y consume presupuesto; el almacenamiento, los secretos,
logs y snapshots retenidos también deben considerarse. Finalizar Academy puede
dejar RDS encendida. Para una pausa de trabajo, el operador puede detenerla:

```bash
aws rds stop-db-instance --region us-east-1 --db-instance-identifier pataporte-dev-postgres
```

Y al retomar:

```bash
aws rds start-db-instance --region us-east-1 --db-instance-identifier pataporte-dev-postgres
```

Detenerla no elimina el costo de almacenamiento. RDS puede volver a iniciarla
automáticamente después de siete días. La protección de borrado debe desactivarse
con un cambio revisado antes de eliminar el stack; su snapshot y los logs retenidos
se administran aparte. No se eliminó ni detuvo la instancia en esta entrega.


## ECR y planes ECS: 26 de octubre

Se completó el stack `pataporte-dev-bootstrap` y la publicación del backend en ECR privado. Las nuevas plantillas son `infra/bootstrap.yaml` y `infra/compute.yaml`; el ejecutor reproducible para CloudShell es `scripts/deploy_ecs.py`. El tag inmutable publicado es `source-8dc1b227edaac905`, digest `sha256:4187b5c4f19d206ed2258bf58a4a81ad0e8f8980a96d3ee71b651e73e83a4c0d`. El escaneo ECR reportó tres hallazgos altos, nueve medios y tres bajos; no es una aprobación de seguridad de producción.

Se validaron las cuatro plantillas con cfn-lint 1.20.0 y CloudFormation. Hay 25 pruebas locales aprobadas: 15 de backend/migración/permisos y diez funcionales. Dentro de la imagen Linux publicada también pasaron las diez pruebas que no requieren PostgreSQL; cinco se omitieron explícitamente.

Los change sets `nat-single-20261026` y `compute-initial-20261026` están preparados (cuatro y 16 altas), pendientes de confirmación de conectividad/acceso. La revisión automática rechazó aplicar la NAT; no se ejecutaron los planes ni Alembic contra RDS. El stack compute en REVIEW_IN_PROGRESS solo representa el plan y no tiene hosts ni tareas desplegados.

`config.deploy_database` agrega una cuenta SQL separada, permisos DML, comprobación de esquema/TLS y prueba CRUD con rollback. No imprime contraseñas ni cambia la contraseña de un rol existente. El ensayo local verificó que la cuenta no puede crear tablas ni modificar Alembic.

La guía HTML incluye el plan detallado, argumentos, comandos y alcance real en las etapas 9.5/9.6. Evidencias: manifiesto, imagen ECR, scan, bootstrap y planes JSON en `docs/evidencias/`; captura `ecs-plan-review-2026-10-26.png`.


## Hito verificado en AWS — 27 de octubre

La autorización explícita del operador permitió ejecutar los planes NAT y ECS. Red y compute terminaron en UPDATE_COMPLETE. La tarea de migración terminó en código 0 sobre RDS, con revisión 0002_seed_vaccines, 15 tablas y cinco vacunas. El servidor confirmó TLS 1.2 y la cuenta pataporte_app pasó CRUD con rollback, sin permisos de creación de esquema/base ni actualización de Alembic.

Después se aplicó api-two-20261027, con una sola modificación de ApiService y sin reemplazo. Dos tareas en dos AZ y dos targets healthy pasaron la verificación. Se detuvo una tarea y ECS creó su reemplazo; luego se repitió la verificación completa de servicio. No se ensayó todavía una caída de host/AZ ni una restauración.

Las evidencias JSON y la captura final están en docs/evidencias, fechadas 2026-10-27. La imagen y el escaneo del 26/10 conservan sus fechas originales. Los hallazgos de seguridad de la imagen siguen abiertos. Los recursos permanecen activos y consumen presupuesto. El ALB sirve únicamente salud; todavía faltan frontend, S3, eventos y despliegue AWS desde GitHub Actions.

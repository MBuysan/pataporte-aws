# PATAPORTE · Bitácora de implementación

Actualizada el 4 de noviembre de 2026. Rama: `feature/preparacion-despliegue-aws`.

Validación local del 03–04/11: **61 pruebas aprobadas** — 35 de backend/migraciones, diez de integración y 16 de protección/operación de despliegues. [Informe y evidencias](evidencias/preparacion-cloud-2026-11-03.json).

Este registro reúne avances, decisiones, pruebas y límites. Los hitos del 25–27 de octubre se consolidaron retrospectivamente a partir de los archivos y evidencias del proyecto. Una prueba local o una plantilla validada no se consideran un despliegue en AWS.

## 25/10/2026 · Un entorno que los tres puedan reproducir
<!-- estado: local; area: base -->

**Qué se hizo.** Se prepararon Compose con PostgreSQL, RabbitMQ, FastAPI, worker, Nginx y Mailpit, secretos locales generados, autenticación común y controles de rol/propiedad.

**Decisión y motivo.** Usar Mailpit para comprobar registro, recuperación y PDF sin depender de Gmail ni enviar mensajes a personas. Nginx concentra las solicitudes en `/api`, lo que permite mantener un mismo origen en desarrollo y en la futura distribución web. Base y AMQP quedan sin puertos publicados al equipo.

**Consecuencia.** El entorno local conserva RabbitMQ aunque el objetivo cloud sea SQS. Cada integrante puede trabajar sin compartir credenciales de Academy.

**Evidencia.** Procedimiento histórico en [primer-hito.md](primer-hito.md); recorrido real en `tests/test_local_flow.py`. Los resultados actuales de estas pruebas se registran en la entrada del 03/11.

## 26/10/2026 · Red y RDS separados de la aplicación
<!-- estado: aws; area: infraestructura -->

**Qué se hizo.** Se desplegaron VPC con subredes públicas, de aplicación y de datos en dos AZ, endpoints gateway y RDS PostgreSQL privado con secreto administrado, cifrado y TLS obligatorio.

**Decisión y motivo.** Separar stacks de red, datos y cómputo permite actualizar contenedores sin reemplazar recursos persistentes. PostgreSQL conserva el modelo existente y evita una migración de motor sin beneficio funcional para esta entrega. La base comenzó Single-AZ para limitar consumo durante la preparación.

**Límite.** Tener subredes en dos AZ no convierte una instancia RDS Single-AZ en una base tolerante a la caída de una AZ. Tampoco se consideró ejecutada la migración SQL al aprobar solamente la configuración de RDS.

**Evidencia.** [Red inicial](evidencias/network-verification-2026-10-26.json), [RDS inicial](evidencias/data-verification-2026-10-26.json). Estos informes corresponden a esa fecha, no a una comprobación actual del saldo o estado.

## 27/10/2026 · API privada sobre ECS y salida controlada
<!-- estado: aws; area: infraestructura -->

**Qué se hizo.** Se habilitaron una NAT y dos rutas de salida para la capa de aplicación, dos hosts t3.micro privados, capacity provider ECS y dos tareas de API distribuidas entre dos AZ. El ALB expone solamente `/health/live` y `/health/ready`.

**Decisión y motivo.** ECS sobre EC2 permite demostrar contenedores, ECR, AMI, Launch Template, EBS y Auto Scaling con una aplicación real. Se reutilizaron `LabInstanceProfile` y `LabRole` por las restricciones de Academy. La NAT permite obtener imágenes, secretos y logs desde los hosts privados.

**Compromisos.** Una sola NAT reduce consumo frente a una por AZ, pero deja una dependencia de la AZ A. El equipo administra capacidad y parches de los hosts. Las tareas verificadas entonces no tenían task role; ejecución y acceso de la aplicación a AWS son responsabilidades distintas.

**Evidencia.** [Red activa](evidencias/network-active-2026-10-27.json), [ECS/ALB](evidencias/compute-verification-2026-10-27.json) y [autorización concreta](evidencias/approval-2026-10-27.json).

## 27/10/2026 · Migración real y usuario SQL limitado
<!-- estado: aws; area: datos -->

**Qué se hizo.** Una tarea privada ejecutó Alembic sobre RDS. Quedaron `0002_seed_vaccines`, quince tablas y cinco vacunas. Se creó `pataporte_app` y se verificaron conexión TLS, CRUD con rollback y restricciones sobre esquema/migraciones.

**Decisión y motivo.** La API usa DML y la tarea de migración usa las credenciales administrativas inyectadas desde Secrets Manager. La API comprueba la versión al arrancar; no crea tablas. Esto hace visibles los despliegues incompletos y evita entregar privilegios DDL a cada réplica.

**Verificación.** Se comprobó además la reposición automática de una tarea en unos 91 segundos. Esa evidencia demuestra recuperación de una tarea, no una caída de host, AZ o región.

**Evidencia.** [Migración](evidencias/migration-2026-10-27.json), [reposición](evidencias/task-replacement-2026-10-27.json). Es la última revisión cloud registrada; la revisión actual sigue bloqueada por acceso.

## 03/11/2026 · Fotos fuera del disco de ECS
<!-- estado: local; area: archivos -->

**Qué se hizo.** Se incorporó `backend/config/storage.py`, serialización de URLs de fotos y adaptación del frontend. La configuración permite guardar archivos locales o en S3 privado.

**Decisión y motivo.** Guardar una referencia `s3://bucket/key` en PostgreSQL y firmar la lectura durante cinco minutos evita persistir enlaces que vencen. El archivo queda disponible aunque ECS reemplace una tarea. Bucket privado, cifrado SSE-S3 y claves aleatorias reducen exposición accidental.

**Validación.** Se limita la entrada a 5 MB y veinte millones de píxeles; Pillow decodifica JPEG/PNG/WebP y vuelve a codificar sin conservar metadatos. El formulario se valida antes de subir. Ante fallo SQL se intenta borrar solo el archivo recién creado; si esa compensación falla, se registra la necesidad de reconciliación.

**Pruebas.** Archivos falsos y sobredimensionados, bucket/prefijo no permitido, referencia sin firma persistida, firma con TTL, formulario inválido sin upload y compensación ante error SQL. Las llamadas S3 se simularon; falta comprobar permisos y objetos reales en Academy.

## 03/11/2026 · La notificación y el cambio se confirman juntos
<!-- estado: local; area: eventos -->

**Qué se hizo.** Se agregó `0003_transactional_outbox` y se cambiaron registro de tutor/veterinario, verificación, recuperación, emisión de pataporte y respaldo por eliminación. La operación y su aviso quedan en la misma transacción PostgreSQL.

**Decisión y motivo.** Publicar después del commit podía perder un aviso si la aplicación caía en medio. Cambiar únicamente RabbitMQ por SQS conservaba ese problema. La outbox permite aceptar el cambio sin que la disponibilidad instantánea del broker decida si el evento se pierde.

**Verificación real.** La migración se aplicó en PostgreSQL local, incluyendo adopción de esquema antiguo, downgrade/replay y permisos DML. Se comprobó que rollback deja fuera tanto al usuario como a su notificación. RDS cloud sigue en la revisión comprobada el 27/10; esta migración nueva todavía no se ejecutó allí.

**Límite.** El tamaño del aviso se acota a 180 KB. Un respaldo mayor necesita un flujo de objetos/referencias antes de habilitar ese caso; actualmente la operación falla y se revierte, sin fingir que se envió el respaldo.

## 03/11/2026 · Publicar con reintentos y un ID estable
<!-- estado: local; area: eventos -->

**Qué se hizo.** Se agregó el proceso `messaging.dispatcher`, también como servicio Compose. Usa RabbitMQ local y puede seleccionar SQS por configuración.

**Separación de secretos.** El publicador tiene configuración de base y broker independientes: la tarea ECS necesita la cuenta SQL DML y acceso SQS, sin recibir el secreto JWT ni credenciales SMTP. El consumidor RabbitMQ también usa configuración de broker independiente de la API.

**Decisión y motivo.** `FOR UPDATE SKIP LOCKED` permite coordinar dos publicadores con PostgreSQL. Solo se marca `dispatched_at` tras el acuse del broker. Los fallos conservan el payload y programan un reintento exponencial acotado; al confirmar la publicación se vacía el payload para reducir retención de códigos y datos clínicos.

**Pruebas.** Broker caído seguido de recuperación, fallo SQL después de publicar con el mismo ID en el reintento y segundo publicador que omite filas bloqueadas. Fueron pruebas contra PostgreSQL real y un emisor controlado; el recorrido RabbitMQ/Mailpit también se ejecutó completo.

**Compromiso.** La entrega es al menos una vez. La transacción mantiene bloqueos durante las llamadas de publicación, por lo que se usan lotes pequeños y timeouts. Falta medir tiempos bajo carga, agregar jitter si corresponde y definir limpieza de filas de diagnóstico.

## 03/11/2026 · Lambda independiente y deduplicación recuperable
<!-- estado: local; area: eventos -->

**Qué se hizo.** Se extrajeron plantillas y generación PDF a `messaging/delivery.py`, con configuración de correo separada de la API. Se agregaron handler Lambda, imagen específica y coordinación DynamoDB.

**Decisión y motivo.** Lambda recibe una instantánea del certificado; no necesita abrir RDS ni conocer el secreto JWT. La imagen usa Python 3.12/Amazon Linux 2023 para disponer de bibliotecas del sistema compatibles con las dependencias actuales; la API conserva Python 3.11. [Base oficial de AWS](https://docs.aws.amazon.com/lambda/latest/dg/python-image.html).

**Coordinación.** DynamoDB registra `PROCESSING`/`DONE`, huella del payload, token de propietario, lease de 120 segundos y TTL de treinta días. Un duplicado completado se omite; un lease activo se reintenta y uno vencido permite recuperación. La función devuelve únicamente los IDs fallidos del lote.

**Pruebas y límite.** Se probaron duplicado, entrega correcta, liberación tras error, lease activo, contrato inválido y lote parcial con respuestas simuladas del SDK. La imagen amd64 se construyó y arrancó sin credenciales de base ni JWT. SMTP puede duplicar un correo si cae el proceso después de su aceptación y antes de marcar el éxito; no se promete exactamente una vez.

## 03/11/2026 · SQS, archivos privados y alarmas definidos
<!-- estado: local; area: infraestructura -->

**Qué se hizo.** Se creó `infra/async.yaml`: bucket privado versionado, política de TLS, cola SQS cifrada, DLQ, DynamoDB on-demand con PITR, función Lambda opcional y suscripción desactivada por defecto.

**Decisiones y motivos.** Cola de origen con cuatro días de retención y DLQ con catorce; visibility timeout de 360 segundos para Lambda de sesenta; cinco recepciones antes de DLQ y concurrencia máxima de dos. Los datos persistentes tienen políticas de retención para no borrarlos al eliminar accidentalmente un stack. Las versiones antiguas de archivos tienen una política explícita de ciclo de vida.

**Observabilidad.** Se definieron alarmas de DLQ/antigüedad y, en `compute.yaml`, targets no saludables, 5xx y memoria. Son alarmas de consola; aún no hay canal de notificación a personas.

**Verificación y límite.** Las seis plantillas pasaron `cfn-lint`. Esto no prueba permisos Academy ni crea recursos. El rol propuesto reutiliza `LabRole` por la restricción del laboratorio; su amplitud no representa una política de mínimo privilegio para producción.

## 03/11/2026 · Frontend HTTPS preparado y publicación por versión
<!-- estado: local; area: archivos -->

**Qué se hizo.** Se creó `infra/edge.yaml` con CloudFront, OAC, bucket privado de frontend, cabeceras de seguridad, caché estática y comportamiento `/api/*` sin caché. La función de borde quita `/api` antes de llamar a FastAPI.

**Decisión y motivo.** Mantener web y API bajo un mismo origen facilita el cliente. OAC limita la lectura del bucket a esa distribución. Las rutas dinámicas reenvían autenticación y no comparten una respuesta de un usuario con otro mediante caché. Se preparó `publish_frontend.py` para subir releases privadas y rechazar reutilizar un ID con contenido diferente.

**Límite que impide considerarlo listo.** La propuesta inicial usa HTTP entre CloudFront y el ALB, protegido por un encabezado secreto. HTTPS del navegador no cifra ese segundo tramo. Falta dominio propio/certificado ACM y cambiar el origen a HTTPS para cargar datos reales. La API pública nueva queda desactivada por defecto; no se desplegó esa apertura.

**Verificación.** Validación de plantilla y prueba que impide sobrescribir otra versión. No hay prueba remota de CloudFront, carga real en S3 ni comprobación visual de esa distribución.

## 03/11/2026 · Migrar antes de cambiar la API
<!-- estado: local; area: entrega -->

**Qué se hizo.** Se agregó un pipeline manual `deploy-academy.yml` y el coordinador `release_academy.py`. Los planes preservan parámetros existentes y las imágenes se identifican por digest. `MigrationImageUri` permite actualizar primero la tarea de migración manteniendo la imagen actual de API.

**Decisión y motivo.** Cambiar todas las tareas a una versión que exige un esquema nuevo antes de migrar puede interrumpir el servicio. El flujo prepara la tarea, ejecuta la migración y verifica su salida; solo después actualiza dos réplicas y comprueba salud/configuración. Se conserva la referencia a la imagen anterior para recuperación compatible.

**Controles probados.** Cuenta incorrecta no llega a CloudFormation; fallo de migración impide la release de API; reemplazo de RDS se rechaza; una release de frontend diferente no se sobrescribe. Los reemplazos de definiciones de tarea ECS se permiten como nuevas revisiones; los recursos con datos no reciben esa excepción.

**Pendiente.** El workflow aún no se ejecutó en GitHub y requiere environment `academy`, revisores, ramas autorizadas y tres credenciales temporales. La entrega automática cubre la API sobre la base inicial; se detiene si detecta la arquitectura con dispatcher, cuyo pipeline conjunto aún falta integrar. No restaura esquemas automáticamente ni elimina datos para recuperar una release.

## 03/11/2026 · Datos del PDF tratados como texto
<!-- estado: local; area: eventos -->

**Qué se corrigió.** Al extraer el generador se identificó que ReportLab interpretaba nombres y descripciones como marcado. Se escapan esos valores y el nombre interpolado en el correo HTML.

**Decisión y motivo.** Un nombre con `&` o `<...>` debe seguir siendo texto, sin romper el certificado ni pedir recursos externos desde el worker. El marcado de la plantilla sigue bajo control del código.

**Verificación.** Se agregó una prueba con nombres que contienen un elemento de imagen remota, signos `<` y `&`; el resultado debe ser un PDF válido y no consultar una URL externa. Su resultado final se registra en el informe local de esta sesión.

## 03/11/2026 · Acceso cloud bloqueado durante esta sesión
<!-- estado: pendiente; area: entrega -->

**Observado.** El usuario inició Academy y abrió la consola en `us-east-1`. La herramienta detectó las pestañas, pero falló al leerlas/controlarlas, incluso tras reconectar su sesión. La cuenta no pudo confirmarse visualmente. AWS CLI funcionó con un perfil ajeno a la cuenta del proyecto; `pataporte-lab` no existía.

**Decisión y motivo.** Detener las operaciones cloud dependientes de esa identidad. Un comando exitoso en una cuenta distinta no sirve como evidencia de PATAPORTE. Se preparó un asistente local opcional de credenciales con entradas ocultas, validación STS y conservación de otros perfiles; el usuario prefirió continuar por navegador y ese asistente no se ejecutó.

**Estado real.** En esta sesión no se aplicaron los stacks nuevos, no se comprobó el saldo actual y no se declararon completadas operaciones que la herramienta no pudo efectuar. Hace falta recuperar el control del navegador o configurar un perfil temporal de la cuenta `476855088538`.

## 03/11/2026 · Correo real, recuperación y entrega final pendientes
<!-- estado: pendiente; area: entrega -->

**Correo.** No hay proveedor SMTP real configurado en Lambda. La plantilla deja `MAIL_DELIVERY_ENABLED=false` y el event source mapping apagado. El evento interno `probe` comprueba SQS/Lambda/DynamoDB/S3 sin enviar mensajes. Antes de activar avisos de usuarios falta integrar el secreto, configurar remitente y probar un destinatario autorizado. Mailpit sí se comprobó localmente.

**Disponibilidad y recuperación.** Faltan restauración de snapshot RDS, caída de host/AZ, carga representativa y escalado medido. La reposición de tarea del 27/10 y los tests unitarios no sustituyen esos ensayos. Las extensiones Scheduler, miniaturas y segunda región siguen siendo propuestas de la guía.

**Trabajo en tres.** Responsable de plataforma: acceso, presupuesto, planes y operación del stack común. Responsable de aplicación/eventos: S3 real, permisos de tareas, entrega SMTP y reintentos. Responsable de calidad/entrega: pipeline conjunto, carga/restauración, evidencias e informe. Cada cambio se revisa por otro integrante y los tres ensayan la defensa completa; no compartir contraseñas de Academy.

**Próximo cierre verificable.** Recuperar acceso → revisar presupuesto y estado → ejecutar `0003` → desplegar async/worker → comprobar probe → integrar correo → entregar web con origen HTTPS → ejecutar pipeline completo y pruebas de recuperación. Cada paso agregará resultado, fecha y evidencia; los pendientes no se convierten en hechos por existir instrucciones.


## 03/11/2026 · Entrega conjunta, correo configurable y pruebas preparadas
<!-- estado: local; area: entrega -->

**Qué se agregó.** El pipeline manual tiene modos `api` y `full`. El coordinador completo prepara imágenes, migra antes de actualizar API/dispatcher, integra async, publica el frontend por versión y comprueba un evento interno sin enviar correo. El modo completo exige dominio, certificado ACM, ARN del secreto SMTP y rol de tareas configurados. No se ejecutó en GitHub ni en AWS.

**Decisiones.** El correo obtiene su configuración desde Secrets Manager en ejecución, con caché de cinco minutos y contraseñas ocultas al representar la configuración. La entrega sigue apagada por defecto. El origen HTTPS usa un dominio y certificado válidos; no se inventa un dominio ni se presenta HTTPS del navegador como cifrado del tramo al ALB. Se preparó escalado opcional de dos a tres tareas con objetivo CPU del 60%; falta comprobar sus permisos y comportamiento en Academy.

**Pruebas de operación.** La carga local autenticada completó 80 solicitudes, cero errores y p95 de 29,506 ms. Es una medición de esta computadora, no de capacidad ni escalado AWS. `restore_rds.py` prepara una restauración a una instancia privada independiente, sin modificar la base original; todavía no se ejecutó ni se verificó SQL/RTO. Una copia restaurada y su snapshot generan costos hasta su limpieza revisada.

## 03/11/2026 · Corrección del formulario de conexión al laboratorio
<!-- estado: local; area: entrega -->

**Problema y causa.** El formulario local devolvía Forbidden. La política `no-referrer` podía convertir el Origin del POST en `null`, incompatible con la comprobación estricta de mismo origen. Un formulario abierto antes de reiniciar también conserva un token CSRF vencido.

**Cambio y motivo.** Se usa `Referrer-Policy: same-origin`, manteniendo la comprobación exacta de Host/Origin y CSRF. Los rechazos muestran un formulario nuevo sin reproducir credenciales; una recarga de `/connect` también permite empezar de nuevo. El servidor continúa limitado a loopback y el perfil se guarda con permisos privados en `.local`, excluido de Git, sin modificar el perfil personal. No se relajó la validación para aceptar orígenes externos.

**Verificación.** Una prueba HTTP con credenciales ficticias comprueba rechazo de Origin null, rechazo de CSRF vencido y aceptación del formulario válido. Pasaron las 14 pruebas de scripts; junto a las 35 de backend y 10 de integración ya registradas, el total local es 59. El usuario volvió a conectar y STS confirmó la cuenta Academy esperada; no se incluyen claves en las evidencias.


## 03/11/2026 · Acceso recuperado, hosts reconstruidos y corrección de SQS
<!-- estado: aws; area: infraestructura -->

**Hechos comprobados.** STS confirmó Academy `476855088538` en `us-east-1`. RDS estaba disponible, privado y cifrado. El ASG conservaba capacidad deseada dos, pero no tenía instancias; las actividades antiguas indicaban `Client.InternalError`. Al solicitar reevaluar la misma capacidad arrancaron dos hosts privados, uno por AZ. No se atribuye una causa definitiva al fallo anterior: AMI disponible, clave EBS habilitada y rol de servicio existente no bastan para identificarla. El ALB volvió a tener dos targets healthy. Un reintento del servicio provocó un tercer host transitorio dentro del máximo ya configurado para renovar las tareas de forma progresiva.

**Imágenes publicadas.** API `api-dbd2c842bb825be4`, digest `sha256:b1f9ae355dae2651f7e03efbd92a64b45ae9fda9930a380ec1d4bd91995ba2c1`; worker `worker-4e404f36bf293cfe`, digest `sha256:32a43ca5adca8edbca168bc87dec2c40e2665bc57eabc7f25ee1d996f49fdf65`. Publicar una imagen no implica que esa versión ya esté ejecutándose.

**Fallo detectado en AWS y corrección.** La creación de async fue revertida porque SQS rechaza una sentencia de política con dos recursos. Se separaron las políticas de cola principal y DLQ, manteniendo la exigencia de TLS. La validación estática había pasado; este caso evidencia su límite frente a restricciones del servicio real.

**Recuperación conservadora.** Bucket, ambas colas, tabla y secreto quedaron retenidos por sus políticas de conservación. Se preparó un plan de importación de esos mismos cinco recursos a CloudFormation, retirando solamente el registro del stack fallido. No se vaciaron colas ni bucket ni se borraron datos para reintentar. Los planes y resultados técnicos quedan en `deployment-results`, excluido de Git; la bitácora registra los resultados sin secretos.

**Límites.** La API nueva y la migración todavía requieren verificación final. El presupuesto actual de Academy no pudo obtenerse mediante AWS Budgets; no se reutiliza el saldo histórico como saldo vigente. Siguen pendientes proveedor SMTP, dominio/certificado y ejecución remota del pipeline.


## 04/11/2026 · Eventos comprobados en AWS y AMI fijada
<!-- estado: aws; area: eventos -->

**Resultado real.** `pataporte-dev-async` terminó en `UPDATE_COMPLETE`. La prueba `scripts/check_async.py` envió un evento interno a SQS, observó `DONE` en DynamoDB y confirmó el archivo cifrado AES256 en S3. Una segunda invocación directa de Lambda, con el mismo evento, terminó sin fallos y conservó una única versión del objeto. Se comprobó deduplicación de ese caso; no se afirma entrega SMTP exactamente una vez. Evidencia: [resultado AWS async](evidencias/aws-async-2026-11-03.json).

**Estado operativo.** La suscripción se habilitó únicamente para la prueba y se volvió a deshabilitar mediante un plan que modificaba solo ese recurso. El correo permaneció apagado durante todo el ensayo. Los objetos de prueba vencen por ciclo de vida a los siete días.

**AMI reproducible.** Un primer plan compute proponía cambiar LaunchTemplate y generaba reemplazos condicionales de ASG/capacity provider: el parámetro público SSM recomendado ya resolvía una AMI diferente. No se ejecutó ese plan. `EcsAmi` pasó a ser un ID explícito y el planificador conserva el `ResolvedValue` realmente desplegado cuando migra desde el parámetro anterior. El nuevo plan eliminó por completo los cambios de hosts/capacity provider. El control contra reemplazos de datos sigue intacto. Una prueba de regresión verifica este caso.

**Restauración en curso.** El snapshot cifrado de ensayo quedó disponible y se inició una copia privada separada. RDS puede informar inicialmente el grupo de parámetros predeterminado mientras está `applying`; se comprobó inmediatamente red/cifrado/privacidad y se conserva la exigencia de grupo correcto al terminar. La copia no se considera validada hasta pasar esas comprobaciones y las consultas SQL. El verificador SQL fue probado localmente sobre las quince tablas de negocio antes de usarlo en la copia.


## 04/11/2026 · Migración completada, API actualizada y verificación final interrumpida
<!-- estado: aws; area: entrega -->

**Migración.** La tarea privada terminó con código cero en `0003_transactional_outbox`: 16 tablas, cinco vacunas, conexión TLS 1.2 y CRUD de prueba con rollback. El usuario de aplicación no puede crear esquema/base ni modificar Alembic. [Resultado SQL](evidencias/migration-2026-11-04.json).

**Entrega API.** Compute terminó en UPDATE_COMPLETE con `pataporte-dev-api:3`. Se revisó una modificación adicional de `ApiMemoryAlarm`: CloudFormation propagaba su dimensión dependiente del nombre de servicio. El control final admite exclusivamente esa alarma existente, sin reemplazo ni eliminación; una prueba rechaza alarmas ajenas, nuevas, eliminaciones y reemplazos. El verificador independiente de API todavía no se ejecutó después de esta actualización: no se presenta como recorrido funcional aprobado.

**Restauración.** La copia `pataporte-restore-20261103-a` está disponible, privada, cifrada y separada de la original, con la misma VPC, grupos de seguridad y parámetros. Falta comparar las tablas desde ECS privado. La copia y snapshot generan costos; la limpieza de la copia sigue pendiente después de conservar evidencia.

**CloudFront y acceso.** El intento de crear edge terminó en ROLLBACK_COMPLETE. Falta leer el evento de error: no se atribuye una causa sin evidencia. Las credenciales Academy vencieron antes de esa consulta y de las verificaciones finales; se reabrió el asistente local corregido para renovarlas, sin usar la cuenta personal. [Estado parcial y límites](evidencias/aws-progress-2026-11-04.json).

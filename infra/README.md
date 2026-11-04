# Infraestructura AWS de Pataporte

Plantillas CloudFormation para AWS Academy Learner Lab (us-east-1, 2 AZ). Todos los roles usan el `LabRole` existente; no se crea IAM.

## Stacks (en orden de despliegue)

| Stack | Plantilla | Tipo | Contenido |
|---|---|---|---|
| `pataporte-network` | `01-network.yml` | persistente | VPC 10.20.0.0/16, subredes públicas/privadas/aisladas, endpoints gateway S3 y DynamoDB, SG de las tareas ECS |
| `pataporte-storage` | `02-storage.yml` | persistente | buckets S3 (uploads; el de frontend quedó sin uso), ECR `pataporte-api` y `pataporte-frontend`, SQS + DLQ, bus EventBridge `pataporte`, Lambda `pataporte-audit`, tópico SNS `pataporte-alarmas`, DynamoDB `pataporte-auditoria` y `pataporte-entregas` (deduplicación del worker, TTL 7 días), secreto de la app |
| `pataporte-nat` | `10-nat.yml` | efímero | NAT Gateway (1 en dev, 1 por AZ en demo) |
| `pataporte-database` | `11-database.yml` | efímero | RDS PostgreSQL 16 (Multi-AZ en demo). Al destruir deja un snapshot final que el próximo deploy restaura |
| `pataporte-app` | `12-app.yml` | efímero | ALB, ECS Fargate (api, worker en Spot, tarea init), autoscaling, alarmas y dashboard |
| `pataporte-edge` | `13-edge.yml` | no se despliega | CloudFront delante del ALB: diseño para una cuenta real; el Learner Lab no permite `cloudfront:CreateDistribution`, así que la app se publica por el ALB (HTTP) |

Los persistentes cuestan casi nada en reposo. Los efímeros (NAT, RDS, ALB, Fargate) cobran por hora: se crean con `deploy` y se borran con `destroy` al terminar de usarlos.

Los nombres de stack son fijos: hay un solo entorno activo a la vez (`dev` o `demo`). Las etiquetas `owner:team`, `owner:environment`, `iac:repo-name` e `iac:version` se aplican a nivel de stack (`deploy-stack.sh`) y CloudFormation las propaga a los recursos.

## Secretos de GitHub

En *Settings > Secrets and variables > Actions*: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` y `AWS_SESSION_TOKEN`, copiados de *AWS Details* del Learner Lab. Vencen con cada sesión del laboratorio: actualizarlos antes de ejecutar los workflows.

Variable opcional (pestaña *Variables*): `ALERT_EMAIL`, ver [Alertas](#alertas).

## Workflows

- **ci**: en cada PR y push a ramas que no sean `main`: pytest, cfn-lint y build de la imagen.
- **deploy** (*Actions > deploy > Run workflow*, elegir `dev` o `demo`): despliega todos los stacks, publica la imagen, corre `init_db` y espera los servicios. La URL del ALB queda en el resumen del job. Un push a `main` solo redespliega si `pataporte-app` ya existe (mantiene su entorno).
- **destroy** (*Run workflow* escribiendo `destroy`): borra edge, app, database y nat y conserva los 2 snapshots más nuevos de la base. Con `include_persistent` también vacía los buckets (todas las versiones) y borra storage y network (el repositorio ECR se borra con sus imágenes); los snapshots se conservan salvo que se marque `delete_snapshots`.

## Backups

- **RDS**: la instancia se llama `pataporte-db`. Al borrar el stack `pataporte-database`, CloudFormation toma un snapshot manual final; `destroy` conserva los 2 más nuevos y borra el resto. Si el stack no existe, `deploy` restaura el snapshot disponible más nuevo (el resumen del job indica cuál) y `init_db` aplica las migraciones pendientes y recrea `pataporte_app`. Si el stack ya existe, se reutiliza el mismo `SnapshotIdentifier`: cambiarlo reemplazaría la base.
- **Empezar con una base vacía**: correr `destroy` con `delete_snapshots`, o borrar a mano los snapshots de `pataporte-db` (*RDS > Snapshots > Manual*) antes del deploy.
- **S3 uploads**: versionado. Las versiones anteriores y borradas se conservan 7 días (1 día bajo `historiales/`).
- **DynamoDB** (`pataporte-auditoria`, `pataporte-entregas`): point-in-time recovery activado (últimos 35 días).

## Alertas

Las alarmas de `12-app.yml` (5xx, latencia y DLQ) notifican al tópico SNS `pataporte-alarmas` al dispararse y al volver a OK. Para recibirlas por email:

1. En *Settings > Secrets and variables > Actions > Variables*, crear la variable de repositorio `ALERT_EMAIL` con la dirección destino.
2. Correr `deploy`: el stack de storage suscribe el email al tópico.
3. Confirmar la suscripción desde el email que envía AWS (*AWS Notification - Subscription Confirmation*). Como el tópico es persistente, la confirmación se mantiene entre redespliegues.

## Valores del secreto de la app

El stack de storage genera `SECRET_KEY` y deja `MAIL_USERNAME`, `MAIL_PASSWORD` y `MAIL_FROM` en `CHANGE_ME`. Para cargarlos:

```bash
arn=$(aws cloudformation describe-stacks --stack-name pataporte-storage \
  --query "Stacks[0].Outputs[?OutputKey=='AppSecretArn'].OutputValue" --output text)
secret_key=$(aws secretsmanager get-secret-value --secret-id "$arn" --query SecretString --output text | jq -r .SECRET_KEY)
aws secretsmanager put-secret-value --secret-id "$arn" --secret-string \
  "{\"SECRET_KEY\":\"$secret_key\",\"MAIL_USERNAME\":\"cuenta@gmail.com\",\"MAIL_PASSWORD\":\"app-password\",\"MAIL_FROM\":\"cuenta@gmail.com\"}"
aws ecs update-service --cluster pataporte --service worker --force-new-deployment
aws ecs update-service --cluster pataporte --service api --force-new-deployment
```

Las tareas leen el secreto al arrancar, por eso hay que forzar un nuevo despliegue. No modificar `GenerateSecretString` en `02-storage.yml`: hacerlo regenera el secreto y pisa estos valores.

## Base de datos: TLS y usuario de la app

- Todas las tareas se conectan a RDS con `DB_SSLMODE=verify-full` contra el bundle de CA de RDS incluido en la imagen (`backend/certs/us-east-1-bundle.pem`).
- La API y el worker usan `pataporte_app`, que solo puede leer y escribir datos (sin DDL). Su contraseña la genera el secreto `AppDbSecret` de `02-storage.yml` (clave `password`).
- La tarea `init_db` usa el usuario maestro (secreto gestionado por RDS): corre `alembic upgrade head` y crea/actualiza `pataporte_app` con esa contraseña. Hasta que corre por primera vez sobre una base nueva, la API no puede leer ni escribir en la base.
- En local (`docker compose`) se usa un solo usuario y sin TLS.

## Despliegue manual (sin GitHub)

```bash
export ENVIRONMENT=dev
infra/deploy-stack.sh pataporte-network infra/01-network.yml
infra/deploy-stack.sh pataporte-storage infra/02-storage.yml
# ...luego 10, 11, 12 (Environment=... ImageTag=...) y 13, como en .github/workflows/deploy.yml
```

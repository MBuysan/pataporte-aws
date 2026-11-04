# Infraestructura AWS de Pataporte

Plantillas CloudFormation para AWS Academy Learner Lab (us-east-1, 2 AZ). Todos los roles usan el `LabRole` existente; no se crea IAM.

## Stacks (en orden de despliegue)

| Stack | Plantilla | Tipo | Contenido |
|---|---|---|---|
| `pataporte-network` | `01-network.yml` | persistente | VPC 10.20.0.0/16, subredes públicas/privadas/aisladas, endpoints gateway S3 y DynamoDB, SG de las tareas ECS |
| `pataporte-storage` | `02-storage.yml` | persistente | buckets S3 (uploads; el de frontend quedó sin uso), ECR `pataporte-api` y `pataporte-frontend`, SQS + DLQ, bus EventBridge `pataporte`, Lambda `pataporte-audit`, DynamoDB `pataporte-auditoria` y `pataporte-entregas` (deduplicación del worker, TTL 7 días), secreto de la app |
| `pataporte-nat` | `10-nat.yml` | efímero | NAT Gateway (1 en dev, 1 por AZ en demo) |
| `pataporte-database` | `11-database.yml` | efímero | RDS PostgreSQL 16 (Multi-AZ en demo). **Los datos se borran al destruir** |
| `pataporte-app` | `12-app.yml` | efímero | ALB, ECS Fargate (api, worker en Spot, tarea init), autoscaling, alarmas y dashboard |
| `pataporte-edge` | `13-edge.yml` | no se despliega | CloudFront delante del ALB: diseño para una cuenta real; el Learner Lab no permite `cloudfront:CreateDistribution`, así que la app se publica por el ALB (HTTP) |

Los persistentes cuestan casi nada en reposo. Los efímeros (NAT, RDS, ALB, Fargate) cobran por hora: se crean con `deploy` y se borran con `destroy` al terminar de usarlos.

Los nombres de stack son fijos: hay un solo entorno activo a la vez (`dev` o `demo`). Las etiquetas `owner:team`, `owner:environment`, `iac:repo-name` e `iac:version` se aplican a nivel de stack (`deploy-stack.sh`) y CloudFormation las propaga a los recursos.

## Secretos de GitHub

En *Settings > Secrets and variables > Actions*: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` y `AWS_SESSION_TOKEN`, copiados de *AWS Details* del Learner Lab. Vencen con cada sesión del laboratorio: actualizarlos antes de ejecutar los workflows.

## Workflows

- **ci**: en cada PR y push a ramas que no sean `main`: pytest, cfn-lint y build de la imagen.
- **deploy** (*Actions > deploy > Run workflow*, elegir `dev` o `demo`): despliega todos los stacks, publica la imagen, corre `init_db` y espera los servicios. La URL del ALB queda en el resumen del job. Un push a `main` solo redespliega si `pataporte-app` ya existe (mantiene su entorno).
- **destroy** (*Run workflow* escribiendo `destroy`): borra edge, app, database y nat. Con `include_persistent` también vacía los buckets y borra storage y network (el repositorio ECR se borra con sus imágenes).

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

## Despliegue manual (sin GitHub)

```bash
export ENVIRONMENT=dev
infra/deploy-stack.sh pataporte-network infra/01-network.yml
infra/deploy-stack.sh pataporte-storage infra/02-storage.yml
# ...luego 10, 11, 12 (Environment=... ImageTag=...) y 13, como en .github/workflows/deploy.yml
```

# Documentación del despliegue paralelo (EC2/ASG)

Los archivos de esta carpeta (`bitacora.md`/`.html`, `guia-despliegue-aws.md`/`.html`, `primer-hito.md` y `evidencias/`) se copiaron sin cambios desde la rama de un compañero de equipo. Documentan su línea de trabajo paralela: un despliegue sobre EC2 con Auto Scaling Group, RabbitMQ y un consumidor Lambda, ejecutado en otra cuenta de AWS Learner Lab. Las evidencias (salidas de stacks, verificaciones, capturas) corresponden a esa cuenta y a esa arquitectura.

La arquitectura que se despliega desde este repositorio es la definida en `infra/` (ECS Fargate detrás de un ALB, RDS, SQS/EventBridge y DynamoDB); ver `infra/README.md`. Las plantillas, scripts y nombres que mencionan estos documentos (`infra/*.yaml`, `scripts/*.py`, `config/migrate.py`, etc.) no forman parte de este repositorio.

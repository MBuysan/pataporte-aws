#!/bin/sh
# crea el bucket, la cola y la tabla de deduplicación que usan backend y worker en desarrollo local
awslocal s3 mb s3://pataporte-uploads || true
awslocal sqs create-queue --queue-name pataporte-eventos
awslocal dynamodb create-table --table-name pataporte-entregas \
  --attribute-definitions AttributeName=id_evento,AttributeType=S \
  --key-schema AttributeName=id_evento,KeyType=HASH --billing-mode PAY_PER_REQUEST >/dev/null || true
awslocal dynamodb update-time-to-live --table-name pataporte-entregas \
  --time-to-live-specification Enabled=true,AttributeName=expira >/dev/null || true

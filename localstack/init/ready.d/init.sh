#!/bin/sh
# crea el bucket y la cola que usan backend y worker en desarrollo local
awslocal s3 mb s3://pataporte-uploads || true
awslocal sqs create-queue --queue-name pataporte-eventos

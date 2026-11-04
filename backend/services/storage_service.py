from functools import cache

import boto3
from botocore.config import Config

from config.settings import settings

URL_EXPIRACION_SEGUNDOS = 3600


@cache
def _s3():
    # AWS_ENDPOINT_URL (LocalStack en local) lo toma boto3 solo
    return boto3.client("s3", region_name=settings.AWS_REGION, config=Config(signature_version="s3v4"))


def subir(key: str, contenido: bytes, content_type: str):
    _s3().put_object(Bucket=settings.UPLOADS_BUCKET, Key=key, Body=contenido, ContentType=content_type)


def descargar(key: str) -> bytes:
    return _s3().get_object(Bucket=settings.UPLOADS_BUCKET, Key=key)["Body"].read()


def url_firmada(key: str) -> str:
    return _s3().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.UPLOADS_BUCKET, "Key": key},
        ExpiresIn=URL_EXPIRACION_SEGUNDOS,
    )

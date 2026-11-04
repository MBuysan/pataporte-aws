"""Private object storage; persist object references, never expiring signed URLs."""
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit
import uuid
import warnings

import boto3
from botocore.config import Config
from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from config.settings import settings

FORMATS = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"), "WEBP": ("webp", "image/webp")}


def client():
    return boto3.client("s3", region_name=settings.AWS_REGION,
                        config=Config(signature_version="s3v4", connect_timeout=3, read_timeout=10,
                                      retries={"max_attempts": 2, "mode": "standard"}))


def validated_image(content):
    if not content or len(content) > settings.PHOTO_MAX_BYTES:
        raise HTTPException(413, "La imagen debe tener contenido y ocupar hasta 5 MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                fmt = image.format
                if fmt not in FORMATS or image.width * image.height > 20_000_000:
                    raise ValueError("Unsupported image")
                image.load()
                output = BytesIO()
                # Decode/re-encode removes metadata and rejects renamed non-images.
                image.save(output, format=fmt)
                cleaned = output.getvalue()
                if len(cleaned) > settings.PHOTO_MAX_BYTES:
                    raise HTTPException(413, "La imagen procesada supera el límite")
                return cleaned, *FORMATS[fmt]
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(400, "El archivo no es una imagen JPEG, PNG o WebP válida") from None


def save_photo(content, owner_id):
    data, extension, content_type = validated_image(content)
    name = uuid.uuid4().hex + "." + extension
    if settings.STORAGE_BACKEND == "s3":
        if not settings.ASSETS_BUCKET:
            raise RuntimeError("Falta ASSETS_BUCKET")
        owner = str(uuid.UUID(str(owner_id)))
        key = f"photos/{owner}/{name}"
        client().put_object(Bucket=settings.ASSETS_BUCKET, Key=key, Body=data,
                            ContentType=content_type, ServerSideEncryption="AES256",
                            CacheControl="private, max-age=300")
        return "s3://" + settings.ASSETS_BUCKET + "/" + key
    if settings.STORAGE_BACKEND != "local":
        raise RuntimeError("STORAGE_BACKEND inválido")
    path = Path("uploads/mascotas") / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return "/" + path.as_posix()


def photo_url(reference):
    if not reference or not reference.startswith("s3://"):
        return reference
    parsed = urlsplit(reference)
    if parsed.netloc != settings.ASSETS_BUCKET or not parsed.path.startswith("/photos/") or ".." in parsed.path:
        raise ValueError("Referencia de objeto no permitida")
    return client().generate_presigned_url("get_object", Params={
        "Bucket": parsed.netloc, "Key": parsed.path.lstrip("/")}, ExpiresIn=300)


def delete_new_photo(reference):
    """Compensate only an upload created by this request when its DB write fails."""
    if reference.startswith("s3://" + settings.ASSETS_BUCKET + "/photos/") and settings.ASSETS_BUCKET:
        client().delete_object(Bucket=settings.ASSETS_BUCKET, Key=urlsplit(reference).path.lstrip("/"))
    elif reference.startswith("/uploads/mascotas/"):
        path = Path(reference.lstrip("/"))
        if path.parent == Path("uploads/mascotas"):
            path.unlink(missing_ok=True)

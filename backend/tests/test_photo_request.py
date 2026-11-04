import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from fastapi import HTTPException
from routers import mascotas


class PhotoRequestTests(unittest.TestCase):
    def request(self, **changes):
        owner = str(uuid4())
        data = dict(id_tutor=owner, nombre="Mascota ficticia", especie="perro", raza=None,
                    fecha_de_nacimiento=None, sexo="hembra", foto=Mock(filename="photo.png", read=AsyncMock(return_value=b"image")),
                    db=Mock(), user={"id": owner, "rol": "tutor"})
        data.update(changes)
        return data

    def test_invalid_form_is_rejected_before_upload(self):
        request = self.request(especie="invalid")
        with patch.object(mascotas, "save_photo") as upload, self.assertRaises(HTTPException) as error:
            asyncio.run(mascotas.registrar_mascota(**request))
        self.assertEqual(error.exception.status_code, 422)
        request["foto"].read.assert_not_awaited()
        upload.assert_not_called()

    def test_failed_database_write_compensates_only_its_new_photo(self):
        reference = "s3://fictional/photos/new-photo.png"
        with patch.object(mascotas, "save_photo", return_value=reference), \
             patch.object(mascotas.mascota_service, "crear", side_effect=RuntimeError("fictional DB failure")), \
             patch.object(mascotas, "delete_new_photo") as cleanup, self.assertRaises(RuntimeError):
            asyncio.run(mascotas.registrar_mascota(**self.request()))
        cleanup.assert_called_once_with(reference)

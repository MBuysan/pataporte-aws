from io import BytesIO
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import HTTPException
from PIL import Image
from config import storage


class StorageTests(unittest.TestCase):
    def image(self):
        buffer = BytesIO()
        Image.new("RGB", (16, 16), "green").save(buffer, format="PNG")
        return buffer.getvalue()

    def test_renamed_non_image_and_oversize_are_rejected(self):
        with self.assertRaises(HTTPException) as invalid:
            storage.validated_image(b'<script>alert("not an image")</script>')
        self.assertEqual(invalid.exception.status_code, 400)
        with patch.object(storage.settings, "PHOTO_MAX_BYTES", 30), self.assertRaises(HTTPException) as large:
            storage.validated_image(self.image())
        self.assertEqual(large.exception.status_code, 413)

    def test_private_s3_upload_persists_reference_and_signs_only_on_read(self):
        s3 = Mock()
        s3.generate_presigned_url.return_value = "https://fictional.s3.amazonaws.com/photo?signature=fictional"
        config = SimpleNamespace(PHOTO_MAX_BYTES=5 * 1024 * 1024, STORAGE_BACKEND="s3", ASSETS_BUCKET="fictional-private-bucket")
        with patch.object(storage, "settings", config), patch.object(storage, "client", return_value=s3):
            reference = storage.save_photo(self.image(), str(uuid4()))
            self.assertTrue(reference.startswith("s3://fictional-private-bucket/photos/"))
            self.assertNotIn("signature", reference)
            s3.generate_presigned_url.assert_not_called()
            url = storage.photo_url(reference)
            self.assertTrue(url.startswith("https://"))
            self.assertEqual(s3.generate_presigned_url.call_args.kwargs["ExpiresIn"], 300)
            request = s3.put_object.call_args.kwargs
            self.assertNotIn("ACL", request)
            self.assertEqual(request["ServerSideEncryption"], "AES256")
            self.assertEqual(request["ContentType"], "image/png")
            with Image.open(BytesIO(request["Body"])) as decoded:
                self.assertEqual(decoded.size, (16, 16))
            with self.assertRaises(ValueError):
                storage.photo_url("s3://another-bucket/photos/secret.png")
            with self.assertRaises(ValueError):
                storage.photo_url("s3://fictional-private-bucket/certificates/secret.pdf")

    def test_cleanup_cannot_delete_another_bucket(self):
        s3 = Mock()
        with patch.object(storage.settings, "ASSETS_BUCKET", "allowed"), patch.object(storage, "client", return_value=s3):
            storage.delete_new_photo("s3://another-bucket/photos/example.png")
        s3.delete_object.assert_not_called()

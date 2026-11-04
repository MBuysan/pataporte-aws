import configparser
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import connect_lab

BLOCK = "[default]\naws_access_key_id=fictional-key\naws_secret_access_key=fictional-secret\naws_session_token=fictional-session\n"


class LabConnectionTests(unittest.TestCase):
    def test_form_origin_and_stale_form_recovery(self):
        server = connect_lab.ThreadingHTTPServer(("127.0.0.1", 0), connect_lab.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/connect") as response:
                self.assertEqual(response.headers["Referrer-Policy"], "same-origin")
                self.assertIn('name="csrf"', response.read().decode())
            for origin, token in [("null", connect_lab.CSRF), (base, "stale-token")]:
                request = Request(base + "/connect", data=urlencode({"csrf": token, "block": BLOCK}).encode(), headers={"Origin": origin})
                with patch.object(connect_lab, "connected", False), patch.object(connect_lab, "validate_and_save") as save:
                    with self.assertRaises(HTTPError) as caught:
                        urlopen(request)
                    self.assertEqual(caught.exception.code, 403)
                    body = caught.exception.read().decode()
                    caught.exception.close()
                    self.assertIn('name="csrf"', body)
                    self.assertNotIn("fictional-secret", body)
                    save.assert_not_called()
            request = Request(base + "/connect", data=urlencode({"csrf": connect_lab.CSRF, "block": BLOCK}).encode(), headers={"Origin": base})
            with patch.object(connect_lab, "connected", False), patch.object(connect_lab, "validate_and_save") as save, patch.object(connect_lab.threading, "Timer"):
                with urlopen(request) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn("Laboratorio conectado", response.read().decode())
                save.assert_called_once_with(BLOCK)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_validated_credentials_are_private_and_isolated(self):
        result = subprocess.CompletedProcess([], 0, stdout=connect_lab.ACCOUNT + "\n", stderr="")
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "aws"
            with patch.object(connect_lab, "STORE", target), patch.object(connect_lab.subprocess, "run", return_value=result) as run, \
                 patch.object(connect_lab.shutil, "which", return_value="/fictional/aws"):
                connect_lab.validate_and_save(BLOCK)
            saved = configparser.RawConfigParser()
            saved.read(target / "credentials")
            self.assertEqual(saved.sections(), [connect_lab.PROFILE])
            self.assertEqual(os.stat(target / "credentials").st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(target).st_mode & 0o777, 0o700)
            self.assertNotIn("fictional-secret", str(run.call_args.args))
            self.assertNotIn("AWS_PROFILE", run.call_args.kwargs["env"])

    def test_wrong_account_writes_nothing(self):
        result = subprocess.CompletedProcess([], 0, stdout="000000000000\n", stderr="")
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "aws"
            with patch.object(connect_lab, "STORE", target), patch.object(connect_lab.subprocess, "run", return_value=result), \
                 patch.object(connect_lab.shutil, "which", return_value="/fictional/aws"), self.assertRaises(ValueError):
                connect_lab.validate_and_save(BLOCK)
            self.assertFalse(target.exists())

    def test_missing_session_token_is_rejected_before_sts(self):
        with patch.object(connect_lab.subprocess, "run") as run, self.assertRaises(ValueError):
            connect_lab.validate_and_save("[default]\naws_access_key_id=fictional\naws_secret_access_key=fictional\n")
        run.assert_not_called()

    def test_page_never_includes_pasted_credentials(self):
        page = connect_lab.page("Verificado", True).decode()
        self.assertNotIn("fictional-secret", page)
        self.assertNotIn("textarea", page.split("</style>")[1])

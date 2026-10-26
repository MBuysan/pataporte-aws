#!/usr/bin/env python3
"""Esperar Compose y ejecutar el mismo recorrido de integración que CI."""
import os
from pathlib import Path
import sys
import time
import unittest
from urllib.request import urlopen

os.environ["PATAPORTE_RUN_INTEGRATION"] = "1"
base = os.getenv("PATAPORTE_BASE_URL", "http://127.0.0.1:8085/api")
deadline = time.monotonic() + 120
while True:
    try:
        with urlopen(base + "/health/ready", timeout=3) as response:
            if response.status == 200:
                break
    except OSError:
        if time.monotonic() >= deadline:
            sys.exit("La API no estuvo lista en 120 segundos")
        time.sleep(1)
suite = unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parents[1] / "tests"))
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())

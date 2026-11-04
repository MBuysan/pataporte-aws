from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import load_probe
import release_full
from restore_rds import validate_restore


class DeliveryOperationsTests(unittest.TestCase):
    def test_full_release_refuses_missing_or_foreign_configuration(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(RuntimeError, "Falta configurar"):
            release_full.configuration()
        config = {"PATAPORTE_API_DOMAIN": "api.example.com", "PATAPORTE_ALB_CERTIFICATE_ARN": "arn:aws:acm:us-east-1:000000000000:certificate/foreign",
                  "PATAPORTE_SMTP_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:476855088538:secret:fictional",
                  "PATAPORTE_TASK_ROLE_ARN": "arn:aws:iam::476855088538:role/LabRole"}
        with patch.dict(os.environ, config, clear=True), self.assertRaisesRegex(RuntimeError, "otra cuenta"):
            release_full.configuration()

    def test_full_release_migration_failure_prevents_all_downstream_deployments(self):
        session = Mock()
        session.client.return_value.get_caller_identity.return_value = {"Account": "476855088538"}
        config = {"fictional": "configuration"}
        release = {"configuration": config, "previous_task": "old:1", "run": "fixture"}
        def run(script, *args):
            if args[0] == "migrate":
                raise subprocess.CalledProcessError(1, "fictional migration")
        with patch.object(release_full, "configuration", return_value=config), \
             patch.object(release_full.boto3, "Session", return_value=session), \
             patch.object(release_full, "outputs", return_value={"ApiTaskDefinitionArn": "old:1"}), \
             patch.object(release_full, "read", return_value=release), \
             patch.object(release_full, "run", side_effect=run), patch.object(release_full, "apply") as apply, \
             patch.object(sys, "argv", ["release_full.py", "deploy"]), self.assertRaises(subprocess.CalledProcessError):
            release_full.main()
        apply.assert_not_called()

    def test_restore_rejects_original_instance_and_exposes_isolation_drift(self):
        source = {"DBInstanceIdentifier": "pataporte-dev-postgres", "Engine": "postgres", "PubliclyAccessible": False,
                  "StorageEncrypted": True, "MultiAZ": False, "DBSubnetGroup": {"VpcId": "vpc-fictional"},
                  "VpcSecurityGroups": [{"VpcSecurityGroupId": "sg-fictional"}],
                  "DBParameterGroups": [{"DBParameterGroupName": "force-tls"}]}
        with self.assertRaises(RuntimeError):
            validate_restore(source, source)
        target = {**deepcopy(source), "DBInstanceIdentifier": "pataporte-restore-fixture"}
        self.assertTrue(all(validate_restore(source, target).values()))
        target["PubliclyAccessible"] = True
        target["DBSubnetGroup"]["VpcId"] = "another-vpc"
        result = validate_restore(source, target)
        self.assertFalse(result["private"])
        self.assertFalse(result["same_vpc"])

    def test_load_metrics_include_errors_and_do_not_store_bearer_token(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return b"[]"
        opener = Mock(return_value=Response())
        result = load_probe.measure("http://127.0.0.1/api", "fictional-private-token", 2, 1, 1000, opener)
        self.assertEqual(result["status_counts"], {"200": 2})
        self.assertTrue(result["authenticated"])
        self.assertEqual(result["errors"], 0)
        self.assertNotIn("fictional-private-token", json.dumps(result))
        self.assertEqual(load_probe.percentile(list(range(1, 101)), .95), 95)

    def test_load_probe_rejects_embedded_credentials_before_any_network(self):
        with self.assertRaises(ValueError):
            load_probe.verify_target("https://user:secret@example.com/api")

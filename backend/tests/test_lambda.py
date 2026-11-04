import hashlib
import json
import os
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

import boto3
from botocore.stub import Stubber
from messaging import lambda_handler as worker


class LambdaTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"IDEMPOTENCY_TABLE": "fictional-events"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.ddb = boto3.client("dynamodb", region_name="us-east-1", aws_access_key_id="fictional", aws_secret_access_key="fictional")
        self.stub = Stubber(self.ddb)
        self.stub.activate()
        self.addCleanup(self.stub.deactivate)
        self.envelope = {"schema_version": 1, "event_id": str(uuid4()), "payload": {"tipo": "probe"}}

    def test_duplicate_does_not_repeat_delivery(self):
        fingerprint = hashlib.sha256(json.dumps(self.envelope["payload"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        self.stub.add_client_error("put_item", service_error_code="ConditionalCheckFailedException")
        self.stub.add_response("get_item", {"Item": {"status": {"S": "DONE"}, "fingerprint": {"S": fingerprint}}},
                               {"TableName": "fictional-events", "Key": {"event_id": {"S": self.envelope["event_id"]}}, "ConsistentRead": True})
        delivery = Mock()
        self.assertEqual(worker.process(self.envelope, self.ddb, delivery), "duplicate")
        delivery.assert_not_called()
        self.stub.assert_no_pending_responses()

    def test_success_is_marked_done_only_after_delivery(self):
        self.stub.add_response("put_item", {})
        self.stub.add_response("update_item", {})
        delivery = Mock()
        self.assertEqual(worker.process(self.envelope, self.ddb, delivery), "processed")
        delivery.assert_called_once_with(self.envelope["payload"], self.envelope["event_id"])
        self.stub.assert_no_pending_responses()

    def test_delivery_failure_releases_lease_and_is_retried(self):
        self.stub.add_response("put_item", {})
        self.stub.add_response("delete_item", {})
        with self.assertRaises(OSError):
            worker.process(self.envelope, self.ddb, Mock(side_effect=OSError("SMTP offline")))
        self.stub.assert_no_pending_responses()

    def test_active_lease_does_not_process_concurrently(self):
        self.stub.add_client_error("put_item", service_error_code="ConditionalCheckFailedException")
        self.stub.add_response("get_item", {"Item": {"status": {"S": "PROCESSING"}}})
        delivery = Mock()
        with self.assertRaises(RuntimeError):
            worker.process(self.envelope, self.ddb, delivery)
        delivery.assert_not_called()

    def test_partial_batch_retries_only_failed_records(self):
        records = [{"messageId": "ok", "body": json.dumps(self.envelope)}, {"messageId": "bad", "body": "not json"}]
        with patch.object(worker, "process", return_value="processed"):
            self.assertEqual(worker.handler({"Records": records}, None), {"batchItemFailures": [{"itemIdentifier": "bad"}]})

    def test_invalid_schema_cannot_be_marked_done(self):
        with self.assertRaises(ValueError):
            worker.process({**self.envelope, "schema_version": 999}, self.ddb, Mock())
        self.stub.assert_no_pending_responses()

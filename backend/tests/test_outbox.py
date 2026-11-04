from datetime import datetime, timezone
import os
import unittest
from unittest.mock import Mock

from sqlalchemy import event, select
from sqlalchemy.orm import sessionmaker
from config.migrate import migrate_database
from config.models import OutboxEvent, UsuarioTutor
from messaging.dispatcher import dispatch_batch
from messaging.publisher import publicar_email
import test_database


@unittest.skipUnless(os.getenv("PATAPORTE_RUN_MIGRATION_TESTS") == "1", "Requiere PostgreSQL local")
class OutboxTests(unittest.TestCase):
    def setUp(self):
        test_database.MigrationTests.setUp(self)
        migrate_database(self.engine)
        self.sessions = sessionmaker(bind=self.engine)

    tearDown = test_database.MigrationTests.tearDown

    def enqueue(self, db):
        return publicar_email({"tipo": "verificacion_email", "email": "fictional@example.com", "codigo": "123456"}, db)

    def test_rollback_keeps_neither_user_nor_notification(self):
        with self.sessions() as db:
            db.add(UsuarioTutor(cedula="FICTITIOUS", nombre="Prueba", email="fictional@example.com", password_hash="fictional"))
            self.enqueue(db)
            db.flush()
            db.rollback()
        with self.sessions() as db:
            self.assertEqual(db.query(UsuarioTutor).count(), 0)
            self.assertEqual(db.query(OutboxEvent).count(), 0)

    def test_broker_outage_preserves_event_until_successful_retry(self):
        with self.sessions.begin() as db:
            event_id = self.enqueue(db)
        offline = Mock(side_effect=OSError("fictional outage"))
        self.assertEqual(dispatch_batch(self.sessions, offline), 0)
        with self.sessions.begin() as db:
            row = db.get(OutboxEvent, event_id)
            self.assertIsNone(row.dispatched_at)
            self.assertEqual(row.payload["codigo"], "123456")
            self.assertEqual(row.attempts, 1)
            self.assertEqual(row.last_error, "broker_unavailable")
            row.available_at = datetime.now(timezone.utc)
        online = Mock()
        self.assertEqual(dispatch_batch(self.sessions, online), 1)
        self.assertEqual(offline.call_args.args[0], online.call_args.args[0])
        with self.sessions() as db:
            row = db.get(OutboxEvent, event_id)
            self.assertIsNotNone(row.dispatched_at)
            self.assertEqual(row.payload, {})
        self.assertEqual(dispatch_batch(self.sessions, online), 0)
        online.assert_called_once()

    def test_dispatched_then_sql_failure_retries_with_identical_event_id(self):
        with self.sessions.begin() as db:
            self.enqueue(db)
        sender = Mock()
        def broken_session():
            db = self.sessions()
            def refuse_commit(session):
                raise RuntimeError("fictional commit failure")
            event.listen(db, "before_commit", refuse_commit)
            return db
        with self.assertRaisesRegex(RuntimeError, "commit failure"):
            dispatch_batch(broken_session, sender)
        self.assertEqual(dispatch_batch(self.sessions, sender), 1)
        self.assertEqual(sender.call_args_list[0].args[0], sender.call_args_list[1].args[0])

    def test_concurrent_dispatcher_skips_locked_event(self):
        with self.sessions.begin() as db:
            locked_id = self.enqueue(db)
            free_id = self.enqueue(db)
        with self.sessions() as locking, locking.begin():
            locking.scalar(select(OutboxEvent).where(OutboxEvent.id == locked_id).with_for_update())
            sender = Mock()
            self.assertEqual(dispatch_batch(self.sessions, sender), 1)
            self.assertEqual(sender.call_args.args[0]["event_id"], free_id)
        self.assertEqual(dispatch_batch(self.sessions, Mock()), 1)

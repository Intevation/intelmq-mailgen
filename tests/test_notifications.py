# -*- coding: utf-8 -*-
"""
Tests for intelmqmail.notifications.
"""

import unittest
from datetime import datetime, timedelta, timezone

from intelmqmail.notification import ScriptContext, Directive


class TestScriptContext(unittest.TestCase):

    def context_with_directive(self, recipient_address="admin@example.com",
                               template_name="generic_plaintext.txt",
                               notification_format="generic_plaintext",
                               event_data_format="inline_csv",
                               aggregate_identifier=(),
                               event_ids=(100001, 100302),
                               directive_ids=(10, 11, 12), inserted_at=None,
                               last_sent=None, notification_interval=None):
        directive = Directive(recipient_address=recipient_address,
                              template_name=template_name,
                              notification_format=notification_format,
                              event_data_format=event_data_format,
                              aggregate_identifier=aggregate_identifier,
                              event_ids=event_ids, directive_ids=directive_ids,
                              inserted_at=inserted_at, last_sent=last_sent,
                              notification_interval=notification_interval)
        return ScriptContext(None, None, None, directive, None)

    def test_notification_interval_exceeded_no_last_sent(self):
        """Notification interval is exceeded if no mail has been sent before"""
        context = self.context_with_directive(
            last_sent=None,
            notification_interval=timedelta(hours=2))
        self.assertTrue(context.notification_interval_exceeded())

    def test_notification_interval_exceeded_last_sent_old_enough(self):
        """Notification interval is exceeded if last mail is too old"""
        context = self.context_with_directive(
            last_sent=datetime.now(timezone.utc) - timedelta(hours=3),
            notification_interval=timedelta(hours=2))
        self.assertTrue(context.notification_interval_exceeded())

    def test_notification_interval_exceeded_last_sent_too_new(self):
        """Notification interval is not exceeded if last mail was sent in interval"""
        context = self.context_with_directive(
            last_sent=datetime.now(timezone.utc) - timedelta(hours=1),
            notification_interval=timedelta(hours=2))
        self.assertFalse(context.notification_interval_exceeded())

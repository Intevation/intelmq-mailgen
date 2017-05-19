# -*- coding: utf-8 -*-
"""
Tests for intelmqmail.notifications.
"""

import unittest
from datetime import datetime, timedelta

from intelmqmail.notification import ScriptContext


class TestScriptContext(unittest.TestCase):

    def context_with_directive(self, last_sent=None,
                               notification_interval=None):
        directive = dict(last_sent=last_sent,
                         notification_interval=notification_interval)
        return ScriptContext(None, None, None, directive, None)

    def test_notification_interval_exceeded_no_last_sent(self):
        """Notification interval is exceeded if no mail has been sent before"""
        context = self.context_with_directive(
            last_sent=None,
            notification_interval=timedelta(hours=2))
        self.assertTrue(context.notification_interval_exceeded())

    def test_notification_interval_exceeded_last_sent_old_enough(self):
        """Notification interval is exceeded if no mail has been sent before"""
        context = self.context_with_directive(
            last_sent=datetime.now() - timedelta(hours=3),
            notification_interval=timedelta(hours=2))
        self.assertTrue(context.notification_interval_exceeded())

    def test_notification_interval_exceeded_last_sent_too_new(self):
        """Notification interval is exceeded if no mail has been sent before"""
        context = self.context_with_directive(
            last_sent=datetime.now() - timedelta(hours=1),
            notification_interval=timedelta(hours=2))
        self.assertFalse(context.notification_interval_exceeded())

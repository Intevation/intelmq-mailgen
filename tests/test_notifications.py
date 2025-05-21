# -*- coding: utf-8 -*-
"""
Tests for intelmqmail.notifications.
"""

import unittest
from datetime import datetime, timedelta, timezone

from intelmqmail.notification import ScriptContext, Directive, SendContext
from intelmqmail.templates import Template


class TestScriptContext(unittest.TestCase):

    def context_with_directive(self, recipient_address="admin@example.com",
                               template_name="generic_plaintext.txt",
                               notification_format="generic_plaintext",
                               event_data_format="inline_csv",
                               aggregate_identifier=(),
                               event_ids=(100001, 100302),
                               directive_ids=(10, 11, 12), inserted_at=None,
                               last_sent=None, notification_interval=None,
                               cur=None):
        directive = Directive(recipient_address=recipient_address,
                              template_name=template_name,
                              notification_format=notification_format,
                              event_data_format=event_data_format,
                              aggregate_identifier=aggregate_identifier,
                              event_ids=event_ids, directive_ids=directive_ids,
                              inserted_at=inserted_at, last_sent=last_sent,
                              notification_interval=notification_interval)
        return ScriptContext(config={'sender': 'intelmqmail@intelmq.example'}, cur=cur, gpgme_ctx=None, directive=directive, logger=None)

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

    def test_email_notification_envelope_to(self):
        """
        Test setting the envelope_to in mail_format_as_csv / EmailNotification
        """
        with unittest.mock.patch('psycopg2.connect', autospec=True) as mock_connect:
            cursor = mock_connect.return_value.cursor
            script_context = self.context_with_directive(cur=cursor)
            with unittest.mock.patch('intelmqmail.notification.ScriptContext.new_ticket_number') as new_ticket_number:
                new_ticket_number.return_value = 1
                email_notifications = script_context.mail_format_as_csv(template=Template.from_strings('${ticket_number} Test Subject', 'Body\n${events_as_csv}'),
                                                                        envelope_tos=['contact@example.com'])  # the internal contact, Envelope-To
            assert len(email_notifications) == 1
            assert email_notifications[0].email.get_all('To') == ['admin@example.com']  # the normal recipient, header-to
            assert email_notifications[0].email.get('Subject') == '1 Test Subject'
            with unittest.mock.patch('smtplib.SMTP', autospec=True) as mock_smtp:
                import smtplib
                email_notifications[0].send(SendContext(cur=cursor, smtp=smtplib.SMTP()))
                mock_smtp.return_value.send_message.assert_called_with(email_notifications[0].email, to_addrs=['contact@example.com'])

    def test_mail_format_as_csv_ticket_number(self):
        """ Test parameter ticket_number of mail_format_as_csv """
        with unittest.mock.patch('psycopg2.connect', autospec=True) as mock_connect:
            cursor = mock_connect.return_value.cursor
            script_context = self.context_with_directive(cur=cursor)
            with unittest.mock.patch('intelmqmail.notification.ScriptContext.new_ticket_number') as new_ticket_number:
                new_ticket_number.return_value = 1
                email_notifications = script_context.mail_format_as_csv(template=Template.from_strings('${ticket_number} Test Subject', 'Body\n${events_as_csv}'),
                                                                        ticket_number=2)
            assert len(email_notifications) == 1
            assert email_notifications[0].email.get('Subject') == '2 Test Subject'
            assert email_notifications[0].ticket == 2

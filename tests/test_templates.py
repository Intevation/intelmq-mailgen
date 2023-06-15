# -*- coding: utf-8 -*-
"""Test the templates module of intelmqmail.

Basic test.

Dependencies:
    (none)
Authors:
 *  Bernhard E. Reiter <bernhard@intevation.de>
"""

import os
import unittest
from datetime import datetime, timedelta, timezone
from logging import getLogger
from tempfile import TemporaryDirectory
from unittest.mock import patch

from intelmqmail import templates
from intelmqmail.notification import Directive, ScriptContext
from intelmqmail.tableformat import build_table_format


table_format = build_table_format(
    "Fallback",
    (("source.asn", "asn"),
     ("source.ip", "ip"),
     ("time.source", "timestamp"),
     ("source.port", "src_port"),
     ("destination.ip", "dst_ip"),
     ("destination.port", "dst_port"),
     ("destination.fqdn", "dst_host"),
     ("protocol.transport", "proto"),
     ))
NOW = datetime.now()
CSV = f'''"asn","ip","timestamp","src_port","dst_ip","dst_port","dst_host","proto"\r
"1","1","{NOW.strftime('%Y-%m-%d %H:%M:%S')}","1","1","1","1","1"'''


def load_events(self, columns):
    return [{i: NOW if i == 'time.source' else '1' for i in columns}]


class TemplatesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        "Sets up a directory structure for all template tests."
        cls.top_dir_obj = TemporaryDirectory()  # will clean itself up
        cls.template_dir = os.path.join(cls.top_dir_obj.name, 'templates')
        os.mkdir(cls.template_dir)

        cls.test_contents = """Subject for report #${ticket}

Body of report #${ticket} for AS ${source.asn}. Events:
${events}"""

        with open(os.path.join(cls.template_dir, "test-template"), "xt") as f:
            f.write(cls.test_contents)

    def test_full_template_filename(self):
        self.assertEqual(
            templates.full_template_filename(self.template_dir, "test-template"),
            os.path.join(self.template_dir, "test-template"))

        self.assertRaises(ValueError,
                          templates.full_template_filename,
                          self.template_dir,
                          "../test-template")

    def test_read_template(self):
        tmpl = templates.read_template(self.template_dir, "test-template")
        subject, body = tmpl.substitute({"ticket": "8172",
                                         "source.asn": "3269",
                                         "events": "<CSV formatted events>"})
        self.assertEqual(subject, "Subject for report #8172")
        self.assertEqual(body, ("Body of report #8172 for AS 3269. Events:\n"
                                "<CSV formatted events>\n"))

    def test_template_from_parameter(self):
        "Tests usage of template given as parameter"
        directive = Directive(recipient_address="admin@example.com",
                              template_name="generic_plaintext.txt",
                              notification_format="generic_plaintext",
                              event_data_format="inline_csv",
                              aggregate_identifier=(),
                              event_ids=(100001, 100302), directive_ids=(10, 11, 12),
                              inserted_at=None, last_sent=datetime.now(timezone.utc) - timedelta(hours=1),
                              notification_interval=timedelta(hours=2))
        context = ScriptContext(config={'sender': 'origin@localhost'}, cur=None, gpgme_ctx=None, directive=directive, logger=getLogger('test_templates'),
                                templates={'generic_plaintext.txt': templates.Template.from_strings('This is the subject!', 'and the body!\n${events_as_csv}')})
        self.assertFalse(context.notification_interval_exceeded())
        with patch.object(ScriptContext, 'load_events', new=load_events):
            with patch.object(ScriptContext, 'new_ticket_number', new=lambda cur: 1):
                retval = context.mail_format_as_csv(format_spec=table_format)
                assert retval[0].ticket == 1
                email = retval[0].email.as_string()
                assert 'Subject: This is the subject!' in email
                assert 'and the body' in email
                assert CSV in email

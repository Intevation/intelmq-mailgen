# -*- coding: utf-8 -*-
"""Test the templates module of intelmqmail.

Basic test.

Dependencies:
    (none)
Authors:
 *  Bernhard E. Reiter <bernhard@intevation.de>
"""

import os
import string
from tempfile import TemporaryDirectory
import unittest


from intelmqmail import templates


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

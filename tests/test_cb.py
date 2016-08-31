# -*- coding: utf-8 -*-
"""Test the cb module of intelmqmail.

Basic test.

Dependencies:
    (none)
Authors:
 *  Bernhard E. Reiter <bernhard@intevation.de>
"""

import unittest

from intelmqmail import cb

class CBTest(unittest.TestCase):

    def test_escape_sql_identifier(self):
        self.assertEqual(cb.escape_sql_identifier('abc.def'), '"abc.def"')
        self.assertEqual(cb.escape_sql_identifier('AB_cde4'), '"AB_cde4"')

        self.assertRaises(ValueError, cb.escape_sql_identifier, 'oh-no')
        self.assertRaises(ValueError, cb.escape_sql_identifier, '%s \\")$')

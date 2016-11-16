# -*- coding: utf-8 -*-
"""Test the intelmqmail.db module.

Basic test.

Dependencies:
    (none)
Authors:
 *  Bernhard E. Reiter <bernhard@intevation.de>
"""

import unittest


from intelmqmail import db


class Tests(unittest.TestCase):

    def test_escape_sql_identifier(self):
        self.assertEqual(db.escape_sql_identifier('abc.def'), '"abc.def"')
        self.assertEqual(db.escape_sql_identifier('AB_cde4'), '"AB_cde4"')

        self.assertRaises(ValueError, db.escape_sql_identifier, 'oh-no')
        self.assertRaises(ValueError, db.escape_sql_identifier, '%s \\")$')

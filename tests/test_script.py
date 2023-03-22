# -*- coding: utf-8 -*-
"""Test the intelmqmail.script module
"""

import os
import string
from tempfile import TemporaryDirectory
import unittest
import logging


from intelmqmail.script import load_scripts


log = logging.getLogger(__name__)


class LoadScriptTest(unittest.TestCase):

    def setUp(self):
        self.tempdir = TemporaryDirectory()

        for filename, contents in self.script_files:
            with open(os.path.join(self.tempdir.name, filename), "xt") as f:
                f.write(contents)

    def tearDown(self):
        self.tempdir.cleanup()


class TestLoadScriptSimple(LoadScriptTest):

    """Very basic load_scripts test, that tests in a rudimentary way

     - that the named entry point function has been extracted

     - the order of the entry points is the one determined by the
       numbers in the script file names.

     - the names associated with the entry point objects
    """

    script_files = [("10preparation.py", """\
def entry_point():
    return "preparation"
"""),
                    ("45special_rule1.py", """\
def entry_point():
    return "special rule 1"
""")]

    def test(self):
        entry_points = load_scripts(self.tempdir.name, "entry_point")
        self.assertEqual([f() for f in entry_points],
                         ["preparation", "special rule 1"])
        self.assertEqual([f.filename for f in entry_points],
                         [os.path.join(self.tempdir.name, name)
                          for name in ["10preparation.py",
                                       "45special_rule1.py"]])


class TestLoadScriptMissingEntryPoint(LoadScriptTest):

    """Test that load_scripts raises an exception if the entry point is missing
    """

    script_files = [("10preparation.py", """\
def main():
    return "preparation"
"""),
                    ("45special_rule1.py", """\
def some_other_function():
    pass
""")]

    def test(self):
        with self.assertLogs("intelmqmail.script") as logs:
            with self.assertRaises(RuntimeError,
                                   msg="Errors found while loading scripts"):
                load_scripts(self.tempdir.name, "main")
        self.assertEqual(logs.output,
                         ["ERROR:intelmqmail.script:Cannot find entry point"
                          " 'main' in '%s'"
                          % os.path.join(self.tempdir.name,
                                         "45special_rule1.py")])


class TestLoadScriptExecErrors(LoadScriptTest):

    """Test that load_scripts raises an exception if loading the module fails
    """

    script_files = [("10preparation.py", """\
def eventhandler(event):
    syntax error
"""),
                    ("45special_rule1.py", """\
def eventhandler(event):
    pass
""")]

    def test(self):
        # use a new logger so that we can test passing an explicit
        # logger to load_scripts
        logger = log.getChild(self.__class__.__name__)
        with self.assertLogs(logger) as logs:
            with self.assertRaises(RuntimeError,
                                   msg="Errors found while loading scripts"):
                load_scripts(self.tempdir.name, "eventhandler", logger=logger)

        # there should be one log message with some specific content
        # (reproducing the whole content would be hard to maintain
        # because of too many irrelevant details in the traceback in the
        # message.
        self.assertEqual(len(logs.output), 1)
        self.assertTrue(logs.output[0].startswith(
            "ERROR:tests.test_script.TestLoadScriptExecErrors:"
            "Exception while trying to find entry point 'eventhandler'"))
        self.assertTrue(logs.output[0].endswith("SyntaxError: invalid syntax"))

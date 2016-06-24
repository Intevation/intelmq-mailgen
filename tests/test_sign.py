# -*- coding: utf-8 -*-
"""Test how to OpenPGP sign data for emails.

First revision without test framework to be directly run.

Dependencies:
 * pygpgme build for python3 (tested with v0.3)
Authors:
 *  Bernhard E. Reiter <bernhard@intevation.de>
"""

from timeit import default_timer as timer
import unittest
from io import BytesIO

import gpgme
from util import GpgHomeTestCase

from os import environ

# Read env var to enable all tests, including tests which may be
# hardware-dependent.
run_all_tests = False
if 'ALLTESTS' in environ:
    if environ['ALLTESTS'] == '1':
        run_all_tests = True

class SignTestCase(GpgHomeTestCase):
    import_keys = ['test1.sec']

    def test_sign_nomime(self):
        email_body = """Hello,

        this is my email body,
        which shall be signed."""

        ctx = gpgme.Context()
        #key = ctx.get_key('5F50 3EFA C8C8 9323 D54C  2525 91B8 CD7E 1592 5678')
        # GnuPG v>=2.0.19 should allow fingerprints with spaces as user ids
        # but some versions (2.0.22 Ubuntu LTS and 2.0.30) have a defect here:
        # https://bugs.gnupg.org/gnupg/issue2382
        # Beside 2.1.11 works, it is better to fall back and do without spaces:
        key = ctx.get_key('5F503EFAC8C89323D54C252591B8CD7E15925678')
        ctx.signers = [key]

        #plaintext = BytesIO(b"Hello World!")
        plaintext = BytesIO(email_body.encode())
        signature = BytesIO()

        sigs = ctx.sign(plaintext, signature, gpgme.SIG_MODE_CLEAR)
        self.assertEqual(len(sigs), 1)

        sig = sigs[0]
        self.assertEqual(sig.type, gpgme.SIG_MODE_CLEAR)
        self.assertIsInstance(sig, gpgme.NewSignature)

        ## print out the unicode string of the signed email body
        #signature.seek(0)
        #print(signature.read().decode())

        # let us verify the signature
        signature.seek(0)
        plaintext = BytesIO()
        vsigs = ctx.verify(signature, None, plaintext)

        plaintext.seek(0)
        self.assertEqual(plaintext.read().decode(), email_body + '\n')
        self.assertEqual(len(sigs), 1)
        vsig = vsigs[0]
        self.assertEqual(vsig.fpr, '5F503EFAC8C89323D54C252591B8CD7E15925678')

    @unittest.skipUnless(run_all_tests,
                         'Set ALLTESTS=1 to include this test.')
    def test_speed(self):
        email_body = """Hello,

        this is my email body,
        which shall be signed."""

        ctx = gpgme.Context()
        key = ctx.get_key('5F503EFAC8C89323D54C252591B8CD7E15925678')
        ctx.signers = [key]

        plaintext = BytesIO(email_body.encode())
        signature = BytesIO()

        start = timer()
        n = 100
        for i in range(n):
            plaintext.seek(0)
            signature.seek(0)

            sigs = ctx.sign(plaintext, signature, gpgme.SIG_MODE_CLEAR)
            self.assertEqual(len(sigs), 1)
            sig = sigs[0]
            self.assertEqual(sig.type, gpgme.SIG_MODE_CLEAR)
            self.assertIsInstance(sig, gpgme.NewSignature)
        end = timer()
        time_spent = end - start # in fractions of seconds
        #print("\nTime elapsed for {:d} iterations: {:.3f}".format(n, time_spent))
        #print("That is {:.1f} signatures per second.".format(n/time_spent))
        #we want to process at least 12 per second
        self.assertTrue(n/time_spent > 12)

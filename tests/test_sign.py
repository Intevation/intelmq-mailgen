"""Test how to OpenPGP-sign data for emails.

 * SPDX-License-Identifier: AGPL-3.0-or-later

 * SPDX-FileCopyrightText: 2016,2021 BSI <https://bsi.bund.de>
 * Software-Engineering: 2016,2021 Intevation GmbH <https://intevation.de>

Dependencies:
 * python3-gpg (official GnuPG Python bindings released with gpgme)
Authors:
 * 2016,2021 Bernhard E. Reiter <bernhard@intevation.de>
"""

from timeit import default_timer as timer
import unittest
from io import BytesIO

import gpg
from .util import GpgHomeTestCase

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

        # from https://www.gnupg.org/documentation/manuals/gpgme/Text-Mode.html
        # | the updated RFC 3156 mandates that the mail user agent
        # | does some preparations so that text mode is not needed anymore.
        ctx = gpg.Context(armor=True, textmode=False, offline=True)

        key = ctx.get_key('5F50 3EFA C8C8 9323 D54C  2525 91B8 CD7E 1592 5678')
        ctx.signers = [key]

        signedText, signResult = ctx.sign(
            email_body.encode(), mode=gpg.constants.sig.mode.CLEAR)
        self.assertEqual(len(signResult.signatures), 1)

        sig = signResult.signatures[0]
        self.assertEqual(sig.type, gpg.constants.sig.mode.CLEAR)
        self.assertIsInstance(sig, gpg.results.NewSignature)

        ## print out the unicode string of the signed email body
        #print('\n' + signedText.decode())

        # let us verify the signature
        newPlainText, results = ctx.verify(signedText)

        self.assertEqual(newPlainText.decode(), email_body + '\n')
        self.assertEqual(len(results.signatures), 1)
        vsig = results.signatures[0]
        self.assertEqual(vsig.fpr, '5F503EFAC8C89323D54C252591B8CD7E15925678')

    @unittest.skipUnless(run_all_tests,
                         'Set ALLTESTS=1 to include this test.')
    def test_speed(self):
        email_body = """Hello,

        this is my email body,
        which shall be signed."""

        ctx = gpg.Context()
        key = ctx.get_key('5F50 3EFA C8C8 9323 D54C  2525 91B8 CD7E 1592 5678')
        ctx.signers = [key]

        plainText = BytesIO(email_body.encode())

        start = timer()
        n = 100
        for i in range(n):
            plainText.seek(0)

            signedText, signResult = ctx.sign(
                plainText, mode=gpg.constants.sig.mode.CLEAR)
            self.assertEqual(len(signResult.signatures), 1)

            sig = signResult.signatures[0]
            self.assertEqual(sig.type, gpg.constants.sig.mode.CLEAR)
            self.assertIsInstance(sig, gpg.results.NewSignature)

        end = timer()
        time_spent = end - start # in fractions of seconds
        #print("\nTime elapsed for {:d} iterations: {:.3f}".format(n, time_spent))
        #print("That is {:.1f} signatures per second.".format(n/time_spent))
        #we want to process at least 12 per second
        self.assertGreater(n / time_spent, 12)

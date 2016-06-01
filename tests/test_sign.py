# -*- coding: utf-8 -*-
"""Test how to OpenPGP sign data for emails.

First revision without test framework to be directly run.

Dependencies:
 * pygpgme build for python3 (tested with v0.3)
Authors:
 *  Bernhard E. Reiter <bernhard@intevation.de>
"""

import unittest
from io import BytesIO

import gpgme
from util import GpgHomeTestCase

class SignTestCase(GpgHomeTestCase):
    import_keys = ['test1.sec']

    def test_sign_nomime(self):
        email_body = """Hello,

        this is my email body,
        which shall be signed."""

        ctx = gpgme.Context()
        key = ctx.get_key('5F50 3EFA C8C8 9323 D54C 2525 91B8 CD7E 1592 5678')
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

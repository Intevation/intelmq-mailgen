#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test how to OpenPGP sign data for emails.

First revision without test framework to be directly run.

Dependencies:
 * pygpgme build for python3
Authors:
 *  Bernhard E. Reiter <bernhard@intevation.de>
"""

import gpgme
from io import BytesIO

def test_sign_nomime():
    #TODO setup a separate GNUPGHOME
    email_body = """Hello,

    this is my email body,
    which shall be signed."""

    ctx = gpgme.Context()

    #TODO create or find test-key
    key = ctx.get_key('2E17923D761D9154B2C1A1763C43F4C8EFF5D42A')
    ctx.signers = [key]

    #plaintext = BytesIO(b"Hello World!")
    plaintext = BytesIO(email_body.encode())
    signature = BytesIO()
    sig = ctx.sign(plaintext, signature, gpgme.SIG_MODE_CLEAR)

    signature.seek(0)
    print(signature.read().decode(), sig[0])

if __name__ == "__main__":
    test_sign_nomime()

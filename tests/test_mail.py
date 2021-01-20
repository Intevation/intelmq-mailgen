""" Tests for intelmqmail.mail.

 * SPDX-License-Identifier: AGPL-3.0-or-later
 * SPDX-FileCopyrightText: 2018,2019,2021 BSI <https://bsi.bund.de>
 * Software-Engineering: 2018,2019.2021 Intevation GmbH <https://intevation.de>

Authors:
 * 2016,2019 Bernhard Herzog <bernhard.herzog@intevation.de>
"""

import unittest
import re
from datetime import datetime, timedelta, timezone

import gpg

from intelmqmail.mail import create_mail

from util import GpgHomeTestCase


class MailCreationTest:

    body_content = ("This body should be using quoted-printable.\n"
                    "From now on, create_mail enforces this,\n"
                    "just like it makes sure the 'From ' on the preceding"
                    " line is escaped.\n")
    csv_content = ('"asn","ip","timestamp"\n'
                   '"64496","192.168.33.12","2018-02-06 11:47:55"\n')

    def create_text_mail_with_attachment(self, gpg_context,
                                         sender="sender@example.com"):
        return create_mail(sender, "recipient@example.com",
                           "Test quoted-printable",
                           self.body_content,
                           [((self.csv_content,),
                             dict(subtype="csv", filename="events.csv"))],
                           gpg_context)

    def check_body_part(self, part):
        """Check that the part's content is the expected body of the message.

        Its contents must match the expected body_content and it must be
        text/plain with a quoted-printable transfer encoding.
        """
        self.assertEqual(part.get_content(), self.body_content)
        self.assertEqual(part.get_content_maintype(), "text")
        self.assertEqual(part.get_content_subtype(), "plain")
        self.assertEqual(part["content-transfer-encoding"], "quoted-printable")

    def check_csv_attachment(self, part):
        """Check that the part's content is the expected csv attacment.

        Its contents must match the expected csv_content and it must be
        text/csv with a quoted-printable transfer encoding.
        """
        self.assertEqual(part.get_content(), self.csv_content)
        self.assertEqual(part.get_content_maintype(), "text")
        self.assertEqual(part.get_content_subtype(), "csv")
        self.assertEqual(part["content-transfer-encoding"], "quoted-printable")

    def check_unpack_multipart(self, part, subtype):
        """Check that part is a multipart with the given subpart.
        Return the parts for further inspection
        """
        self.assertEqual(part.get_content_maintype(), "multipart")
        self.assertEqual(part.get_content_subtype(), subtype)
        return list(part.iter_parts())

    def check_no_from(self, msg):
        """Check that msg has no lines starting with 'From '.

        The serialized representation of msg must not contain any line
        starting with "From ".
        """
        self.assertNotRegex(str(msg), re.compile("^From ", re.MULTILINE))


class TestCreateUnsignedMail(MailCreationTest, unittest.TestCase):

    def test_unsigned_text_mail_with_attachment(self):
        """Test one simple notification message with an attachment."""
        msg = self.create_text_mail_with_attachment(None)
        self.check_no_from(msg)

        # the mail itself is multipart/mixed with the first part being
        # the body and the second the CSV attachment
        body, csv = self.check_unpack_multipart(msg, "mixed")
        self.check_body_part(body)
        self.check_csv_attachment(csv)

    def test_message_id_with_display_name_in_sender(self):
        """Test Message-ID when sender contains a display name.

        The domain of the Message-ID is derived from the sender.
        Originally this was done in a naive way because the code assumed
        the sender to be given in the user@domain form. When the sender
        includes a display name, this must be done differently.
        """
        msg = self.create_text_mail_with_attachment(None,
                                          sender="Real Name <rn@example.com>")
        self.assertRegex(msg["Message-ID"], r"@example\.com>$")

    def test_message_id_with_plain_email_address_in_sender(self):
        """Test Message-ID when sender is a plain email address.
        """
        msg = self.create_text_mail_with_attachment(None,
                                          sender="rn@example.com")
        self.assertRegex(msg["Message-ID"], r"@example\.com>$")


class TestCreateSignedMail(MailCreationTest, GpgHomeTestCase):

    import_keys = ['test1.sec']

    def test_signed_text_mail_with_attachment(self):
        """Test one simple signed notification message with an attachment."""
        ctx = gpg.Context()
        key = ctx.get_key('5F503EFAC8C89323D54C252591B8CD7E15925678')
        ctx.signers = [key]

        msg = self.create_text_mail_with_attachment(ctx)
        ## print mail
        # print(msg)
        self.check_no_from(msg)

        # the mail itself is multipart/signed with the first part being
        # the signed part the second the signature
        signed, signature = self.check_unpack_multipart(msg, "signed")
        self.assertEqual(signature.get_content_type(),
                         "application/pgp-signature")

        # the signed part is multipart/mixed with the first part being
        # the body and the second the CSV attachment
        body, csv = self.check_unpack_multipart(signed, "mixed")
        self.check_body_part(body)
        self.check_csv_attachment(csv)


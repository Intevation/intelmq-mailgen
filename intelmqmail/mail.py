"""Email-related functions"""

import logging
import io
import email.charset
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate

import gpgme


log = logging.getLogger(__name__)


def create_mail(sender, recipient, subject, body, attachments):
    """Create an email either as single or multi-part with attachments."""

    # Encode utf-8 content QP (not base64) for better human
    # readability:
    email.charset.add_charset('utf-8', email.charset.QP, email.charset.QP,
                              'utf-8')

    if len(attachments) == 0:
        msg = MIMEText(body, _charset="utf-8")
    else:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, _charset="utf-8"))

        for filename, contents, maintype, subtype in attachments:
            part = MIMEBase(maintype, subtype, filename=filename)
            part.set_payload(contents)
            msg.attach(part)

    msg.add_header("From", sender)
    msg.add_header("To", recipient)
    msg.add_header("Subject", subject)
    msg.add_header("Date", formatdate(timeval=None, localtime=True))

    return msg


def clearsign(gpgme_ctx, text):
    plaintext = io.BytesIO(text.encode())
    signature = io.BytesIO()

    try:
        sigs = gpgme_ctx.sign(plaintext, signature, gpgme.SIG_MODE_CLEAR)
    except:
        log.error("OpenPGP signing failed!")
        raise

    signature.seek(0)
    return signature.read().decode()

"""Email-related functions"""

import logging
import io
import re
from email.message import EmailMessage
from email.contentmanager import ContentManager, raw_data_manager
from email.policy import SMTP
from email.utils import formatdate

import gpgme


log = logging.getLogger(__name__)


# Map gpgme hash algorithm IDs to OpenPGP/MIME micalg strings. GPG
# supports more algorithms than are listed here, but this should cover
# the algorithms that are likely to be used.
hash_algorithms = {
    gpgme.MD_SHA1: "pgp-sha1",
    gpgme.MD_SHA256: "pgp-sha256",
    gpgme.MD_SHA384: "pgp-sha384",
    gpgme.MD_SHA512: "pgp-sha512",
    }


class FromQuotingContentManager(ContentManager):
    """ContentManager that handles "From " for quoted printable.

    This content manager delegates all functionality to the
    raw_data_manager except when setting text in quoted printable
    transfer encoding. In text mails, the string "From " at the
    beginning of the line can be problematic because for some tools it
    indicates the beginning of a message and some mail agents therefore
    modify such mails by prepending a '>' character to the line. That
    would break any cryptographic signature, so we force
    quoted-printable if necessary and replace "From " with "From=20" in
    the quoted printable encoded text.
    """

    def get_content(self, msg, *args, **kw):
        raw_data_manager.get_content(msg, *args, **kw)

    def set_content(self, msg, obj, *args, **kw):
        replace_from = False

        if (isinstance(obj, str)
                and kw.get("cte") not in ("quoted-printable", "base64")
                and re.search("^From ", obj, re.MULTILINE) is not None):
            kw["cte"] = "quoted-printable"
            replace_from = True

        raw_data_manager.set_content(msg, obj, *args, **kw)

        if (msg.get("content-transfer-encoding") == "quoted-printable"
                and replace_from):
            content = msg.get_payload(decode=False)
            from_escaped = content.replace("From ", "From=20")
            msg.set_payload(from_escaped)


openpgp_policy = SMTP.clone(cte_type="7bit",
                            content_manager=FromQuotingContentManager())


def create_mail(sender, recipient, subject, body, attachments, gpgme_ctx):
    """Create an email either as single or multi-part with attachments.
    """
    msg = EmailMessage(policy=openpgp_policy)
    msg.set_content(body)
    msg.make_mixed()
    signed_part = next(msg.iter_parts())

    if attachments:
        for args, kw in attachments:
            signed_part.add_attachment(*args, **kw)

    if gpgme_ctx is not None:
        signed_bytes = signed_part.as_bytes()
        hash_algo, signature = detached_signature(gpgme_ctx, signed_bytes)

        msg.add_attachment(signature, "application", "pgp-signature",
                           cte="8bit")
        # the signature part should now be the last of two parts in the
        # message, the first one being the signed part.
        signature_part = list(msg.iter_parts())[1]
        if "Content-Disposition" in signature_part:
            del signature_part["Content-Disposition"]

        msg.replace_header("Content-Type", "multipart/signed")

        micalg = hash_algorithms.get(hash_algo)
        if micalg is None:
            raise RuntimeError("Unexpected hash algorithm %r from gpgme"
                               % (signature[0].hash_algo,))

        msg.set_param("protocol", "application/pgp-signature")
        msg.set_param("micalg", micalg)

    msg.add_header("From", sender)
    msg.add_header("To", recipient)
    msg.add_header("Subject", subject)
    msg.add_header("Date", formatdate(timeval=None, localtime=True))

    return msg


def clearsign(gpgme_ctx, text):
    plaintext = io.BytesIO(text.encode())
    signature = io.BytesIO()

    try:
        gpgme_ctx.sign(plaintext, signature, gpgme.SIG_MODE_CLEAR)
    except Exception:
        log.error("OpenPGP signing failed!")
        raise

    signature.seek(0)
    return signature.read().decode()


def detached_signature(gpgme_ctx, plainbytes):
    """Create a detached signature for multipart/signed messages.
    The signature created by this function is asci armored because
    that's required for multipart/signed messages.

    Args:
        gpgme_ctx (gpgme context): The gpgme context to use for signing.
            The signature is made with whatever keys are set as signing keys
            in this context.
        plainbytes (bytes): The data to sign

    Return:
        Tuple of (hash_algo, signature). The hash_algo is one of the
            relevant constants in gpgme. The signature is a bytestring
            with the signature.
    """
    signature = io.BytesIO()

    try:
        gpgme_ctx.armor = True
        sigs = gpgme_ctx.sign(io.BytesIO(plainbytes), signature,
                              gpgme.SIG_MODE_DETACH)
    except Exception:
        print("OpenPGP signing for multipart/signed failed!")
        raise

    signature.seek(0)
    return (sigs[0].hash_algo, signature.read())

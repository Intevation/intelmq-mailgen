Mailgen Scripts (formats)
=========================

For the overall concept of mailgen scripts (also: formats), please see
:ref:`mailgen_scripts`.

Format spec (also: table format)
--------------------------------

The format spec specifies which parts of the data event will become part of the
data sent (usually CSV format) in the notifications (usually e-mail).

This corresponds to the CSV columns in most cases.

The format spec can be set in different ways for the notifications. The order
is the following:

 1. The table format specified by the mailgen script: ``create_notifications`` returning ``context.mail_format_as_csv(table_format, ...)``
 2. The parameter passed to ``cb.create_notifications``/``cb.send_notifications``/``cb.start``/``cb.mailgen``/``intelmqmail.notification.ScriptContext``.
    IntelMQ Webinput CSV uses this.
 3. The internal default, see :py:mod:`intelmqmail.notification.ScriptContext`

Different Envelope-To from Header-To
------------------------------------

Normally, the recipient (Header-To and Envelope-To) of the E-Mail is the ``recipient_address`` of the Directive.
Format Scripts can generate ``EmailNotification`` objects with a differing Envelope-To.

``context.mail_format_as_csv`` takes an argument ``envelope_tos`` with a list of email-addresses.
The Header-To is always taken from the directive.

This feature can be used to send a copy of notifications to internal contacts,
with the original Header-To intact, possibly with different template or format than the original notification.

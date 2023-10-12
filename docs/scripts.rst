Mailgen Scripts (formats)
=========================

For the overall concept of mailgen scripts (also: formats), please see
:ref:`mailgen_scripts`.

Format spec (also: table format)
--------------------------------

The data (usually CSV format) in the notifications (usually e-mail)

 1. The table format specified by the script
 2. The parameter passed to ``cb.create_notifications``/``cb.send_notifications``/``cb.start``/``cb.mailgen``/``intelmqmail.notification.ScriptContext``.
    IntelMQ Webinput CSV uses this.
 3. The internal default, see :py:mod:`intelmqmail.notification.ScriptContext`

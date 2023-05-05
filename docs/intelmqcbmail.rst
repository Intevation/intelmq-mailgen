intelmqcbmail tool
==================

``intelmqcbmail`` is the command line tool to start mailgen.

Command line parameters
-----------------------

* ``-h``, ``--help`` to show a short help page
* ``-a``, ``--all``: Process all events (batch mode) non-interactively
* ``-c CONFIG``, ``--config CONFIG``: Alternative system configuration file
* ``-v``, ``--verbose``: Activate verbose debug logging
* ``-n``, ``--dry-run``: Dry run. Simulate only.

Dry run (simulation)
--------------------

This mode does not send mails and does not mark the directives as sent in the database.

All notifications are generated as if they were sent, which tests the complete configuration, templating etc.
A connection SMTP server is only opened for testing.

The ticket numbers counter is always incremented, as `Postgres sequence changes cannot be rolled back <https://www.postgresql.org/docs/15/functions-sequence.html>`_.

intelmqcbmail tool
==================

``intelmqcbmail`` is the command line tool to start mailgen.

Configuration file
------------------

A complete example configuration file is in the repository, called `intelmq-mailgen.conf.example`.
This example file is also part of the packages and can be found in `/etc/intelmq/`

To set the default logging level, use this configuration key:

.. code-block:: json

    "logging_level": "INFO"


OpenPGP
~~~~~~~

To use OpenPGP, the Unix user running `intelmqcbmail` needs to have the corresponding key available in their keyring.
Example:

.. code-block:: json

    "openpgp": {
        "gnupg_home" : "/etc/intelmq/mailgen/gnupghome",
        "always_sign" : true,
        "signing_key" : "5F503EFAC8C89323D54C252591B8CD7E15925678"
    },

To disable OpenPGP-signing, use these parameters:

.. code-block:: json

    "openpgp": {
        "gnupg_home" : null,
        "always_sign" : false,
        "signing_key" : null
    },


.. _database-1:

Database
--------

The database section in the configuration may look like:

.. code-block:: json

       "database": {
           "event": {
               "name": "intelmq-events",
               "username": "intelmq_mailgen",
               "password": "your DB password",
               "host": "localhost",
               "port": 5432
           },
           "additional_directive_where": ""
       },

The database user needs write-access to the table `sent` and read-access to the tables `directives` and `events`.

The ``additional_directive_where`` parameter is optional and can contain SQL
code appended to the ``WHERE`` clause of the ``SELECT`` operation on the
table ``directives``. The ``AND`` is appended automatically. The columns
of table ``directives`` are available as ``d3`` and the columns of table
``events`` as ``events``. Normally the table ``events`` is not queried
and only joined for the where statement if
``additional_directive_where`` contains ``events.``. Examples:

::

           "additional_directive_where": "\"template_name\" = 'qakbot_provider'"
           "additional_directive_where": "events.\"feed.code\" = 'oneshot'"

Mind the correct quoting. If access to the table events is required, the
used postgres user needs ``UPDATE`` permissions access to the table.
This is by default not the case for mailgen-installations! This
imperfection is a result of the update-locking on the table
``directives`` and the join of ``events`` in the same sub-statement.

Templates and Scripts
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json

    "template_dir": "/etc/intelmq/mailgen/templates",
    "script_directory": "/etc/intelmq/mailgen/formats",

E-Mail settings
~~~~~~~~~~~~~~~

.. code-block:: json

    "sender": "noreply@example.com",
    "smtp": {
        "host": "localhost",
        "port": 25
    },


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

IntelMQ Mailgen
===============

IntelMQ command line tool to process events.

Call ``intelmqcbmail --help`` to see the current usage.

The concept’s documentation can be found here:
https://intevation.github.io/intelmq-mailgen/

Installation
============

Dependencies
------------

These libraries and programs are required:

- The python library ``psycopg2`` (``python3-psycopg2``) for PostgreSQL communication.
- The python library ``gpg`` (``python3-gpg``), part of the library gpgme. Due
  to issues with Ubuntu 20.04, this dependency is not installed when
  installed with ``pip`` or ``setup.py`` Other means of distributions (deb
  packages) are not affected by this bug.
- GnuPG (v>=2.2) for ``python3-gpg``.

As a Python3 application, see the ``install_requires`` section in
setup.py for its dependencies.

If you install the deb-packages, the package management handles all
dependencies.

For an installation from source use this command:

::

   pip3 install -v -e .

**In order to use IntelMQ Mailgen, you require a working
certbund-contact-expert in IntelMQ, as Mailgen makes use of information
and data which is not available in the IntelMQs default fields.**

IntelMQ Configuration
---------------------

For Mailgen to work, the following IntelMQ bots will need to be
configured first:

1. Expert: CERT-bund Contact Database
2. Expert: CERT-bund Contact Rules
3. Output: PostgreSQL

You **must follow the setup instructions for these bots** before setting
up Mailgen.

Database
--------

The ``intelmq-events`` database and the ``intelmq`` database-user should
already have been set up by the configuration of a PostgreSQL output bot
(SQL output bot with engine `postgresql`).
For use with Mailgen this setup has to be extended:

As database-superuser (usually via system user postgres):

1. Create a new database-user:

   ::

      createuser --encrypted --pwprompt intelmq_mailgen

2. Extend the database: ``psql -f sql/notifications.sql intelmq-events``

3. Grant ``intelmq`` the right to insert new events via a trigger:
   ``psql -c "GRANT eventdb_insert TO intelmq" intelmq-events``

4. Grant the new user the right to send out notifications:
   ``psql -c "GRANT eventdb_send_notifications TO intelmq_mailgen" intelmq-events``

Interaction with IntelMQ and the events database
------------------------------------------------

The events written into the events database have been processed by the
rules bot which adds notification directives to the events. The
directives tell mailgen which notifications to generate based on that
event. The statements in ``sql/notifications.sql`` add triggers and
tables to the event database that process these directives as they come
in and prepare them for use by mailgen. In particular:

- The ``directives`` table contains all the directives. The main
  attributes of a directive are

  - ID of the event
  - recipient address
  - data format
  - template name (see “Templates” below)
  - how to aggregate
  - whether and when it was sent. this is the ID of the corresponding
    row in the ``sent`` table (see below)

- When a new event is inserted into the ``events`` table, a trigger
  procedure extracts the directives and inserts them into
  ``directives``.

- The ``sent`` table records which notifications have actually been
  sent. Its main attributes are

  - the ticket number generated for the notification
  - a time stamp indicating when it was sent

When mailgen processes the directives, it reads the still unsent
directives from the database, aggregates directives that are
sufficiently similar that they could be sent in the same mail and calls
a series of scripts for each of the aggregated directives. These scripts
inspect the directive and if they can process the directive generate
mails from it. mailgen then sends these mails and records it in the
``sent`` table.

Ticket Numbers
--------------

For every email sent by Mailgen a ticket number is generated. If a mail
was successfully sent, this number is stored in the table ``sent``,
together with a timestamp when the mail was sent.

Configuration
=============

``intelmq-mailgen`` currently searches for configuration files in two
places:

1. ``$HOME/.intelmq/intelmq-mailgen.conf`` (user configuration file) and
2. ``/etc/intelmq/intelmq-mailgen.conf`` (system configuration file).

Settings are read from both files with the one in the user’s home
directory taking precedence.

The system configuration file path can be overridden with the
``--config`` command line parameter.

Both files must be in JSON format. A complete example can be found in
``intelmq-mailgen.conf.example``.

OpenPGP Signatures
------------------

``gnupg_home`` has to point to the GnuPG home directory for email
signatures. It must:

- contains the private and public key parts for the OpenPGP signature
  without password protection.
- is read/writable for the user running intelmq-mailgen.

For example, the following steps will create such a directory and import
a test signing key.

::

   GNUPGHOME=/tmp/gnupghome mkdir $GNUPGHOME
   chmod og-rwx $GNUPGHOME
   GNUPGHOME=/tmp/gnupghome gpg2 --list-secret-keys
   GNUPGHOME=/tmp/gnupghome gpg2 --import src/intelmq-mailgen/tests/keys/test1.sec

Depending on your GnuPG version you may want to set additional options
by editing ``$GNUPGHOME/gpg.conf``.

For example, the following settings will set the default digest
algorithm, suppress emitting the GnuPG version, and add a comment line
for signatures:

::

   personal-digest-preferences SHA256
   no-emit-version
   comment Key verification <https://example.org/hints-about-verification>

(See the GnuPG documentation for details.)

Now, you should be able to sign using this key without being prompted
for a passphrase. Try, for example:

::

   echo Moin moin. | GNUPGHOME=/tmp/gnupghome gpg2 --clearsign --local-user "5F503EFAC8C89323D54C252591B8CD7E15925678"

Templates
---------

mailgen comes with a templating mechanism that the scripts that process
the directives can use. This mechanism assumes that all templates are
files in the directory from the ``template_dir`` setting in the
configuration file.

The scripts that come with mailgen simply take the template name from
the directive they are processing. This means that the name is set by
the rules used by the rules bot, so see its documentation and
configuration for which templates you need.

Template Format
---------------

The first line of a template file is used as the subject line for mails.
The remaining lines will become the mail body. The body may optionally
be separated from the subject line by one or more empty lines.

Both subject and body text will be interpreted as `Python3 Template
strings <https://docs.python.org/3/library/string.html#template-strings>`__
and may allow some substitutions depending on the format. Subject and
body allow the same substitutions.

Typically supported substitutions:

- All formats:

  - ``${ticket_number}``

- Additional substitutions for CSV-based formats:

  - ``${events_as_csv}`` for the CSV-formatted event data. This is only
    useful in the body.

- When aggregating by event fields the event fields can also be used.
  E.g. if a directive aggregates by ``source.asn`` you can use
  ``${source.asn}``

  Like the template name, aggregation is determined by the rules bot, so
  see there for details.

.. _database-1:

Database
--------

The database section in the configuration may look like:

::

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

``additional_directive_where`` parameter is optional and can contain SQL
code appended to the ``WHERE`` clause of the ``SELECT`` operation on the
table ``directives``. The ``AND`` is appended automatically. The columns
of table ``directives`` are available as ``d3`` and the columns of table
``events`` as ``events``. Normally the table ``events`` is not queried
and only joined for the where statement if
``additional_directive_where`` contains ``events.``. Examples:

.. code:: json

           "additional_directive_where": "\"template_name\" = 'qakbot_provider'"
           "additional_directive_where": "events.\"feed.code\" = 'oneshot'"

Mind the correct quoting. If access to the table events is required, the
used postgres user needs ``UPDATE`` permissions access to the table.
This is by default not the case for mailgen-installations! This
imperfection is a result of the update-locking on the table
``directives`` and the join of ``events`` in the same sub-statement.

Operation manual
================

The logfile shall be monitored for errors to detect unwanted conditions.
Especially grep for:

::

    * 'ERROR'
    * 'Error:'

Each error condition should be handled by an administrator or service
technician soon. It is recommended to use a monitor system to notify
administrators as soon as such a string occurs in the log.

Log file contents
^^^^^^^^^^^^^^^^^

There should be no ``Traceback`` or other ERROR information in the log
of mailgen. Please read the lines in question, often they have good
hints about cause of the failure. Some problem may be solved by
correcting the configuration.

INFO lines appear during normal operations. One condition to get an INFO
message is if Mailgen detects that it is already running to that a
second instance does not start. If this is the case, the running Mailgen
process may still have problems and during the nature of log file, the
messages of the Mailgen that tries to start up, may appear interwoven
with the error conditions.

Mailgen needs to lock db rows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

During a run, if mailgen is started a second time, it will fail to lock
the necessary rows in the database. The ``postgres.log`` file will
record the failed locks, e.g. like

::

   2020-12-15 09:00:02 UTC ERROR:  could not obtain lock on row in relation "directives"

which can be ignored.

Mailgen tries to continue
^^^^^^^^^^^^^^^^^^^^^^^^^

Mailgen will try to continue processing directives and sending mails,
even if some batch of mails could not be send for several reasons.

If it can’t find templates, for instance, it will continue with the next
directive and log an error message and the stacktrace. The error message
contains information about the directives that could not be processed.
The ``directive_ids`` part in the output is a list with the IDs of the
rows in the ``directives`` table and ``event_ids`` a list with ids for
events in the ``events`` table.

This information can be used by an administrator to see which events and
emails may not have gone out in detail, to deal with them later,
possibly with a small script depending on the problem cause.

Developer Information
=====================

Database schema
---------------

Generated using pgadmin4's `ERD tool <https://www.pgadmin.org/docs/pgadmin4/latest/erd_tool.html>`_:

.. image:: contactdb-design.png

The source file is at `intelmq-certbund-contact/sql/contactdb.erd <https://github.com/Intevation/intelmq-certbund-contact/blob/master/sql/contactdb.erd>`_.

Security Considerations
-----------------------

- It is assumed that we need to protect against malicious external data
  coming to us via the database.
- We do not need (or can) protect against local attacks with
  administration rights.
- As our command will be able to run with and without user interaction,
  we assume that only users with administration rights have access to
  the machine and are allowed to start the interactive variant.
- The private key material for signing will have no extra protection by
  passphrase, thus the system itself needs to be secured adequately.
  (This can include separating the setup of intelmq itself on a
  different machine with only access to fill the database.)
- We should pay attention to preventing that the complete system becomes
  an effective signature (or encryption) oracle. To explain: Consider an
  attacker who will receive an automatic notification from our system.
  If this attacker also can trigger a warning over an used feed, she may
  partly control which plaintext is to be signed (or somewhere
  encrypted) and gets the automated result. There is a small potential
  under some circumstances that this can be used for an
  adaptive-plaintext attack.

Column Names
------------

It is possible to define names for the CSV-columns in code. For instance
in ``example_scripts/10shadowservercsv.py``, the dictionary
``standard_column_titles`` maps event field names to column titles.
These are used by most of the CSV formats later defined in
``table_formats``. The formats specified there can still use special
column titles if necessary.

Transformations
---------------

Currently, data is not transformed when it is being added to the CSV
output.

Mailgen always removes the “UTC” notations from time stamps in
``time.source``. It ensures that time stamps will always be UTC.

Testing
-------

An easy way to test the actual sending of emails is to use Python’s
``smtpd`` module running the ``DebuggingServer``:

::

   python3 -m smtpd -d -n -c DebuggingServer localhost:8025

(Don’t forget to configure the corresponding SMTP host and port in your
config.)

If you want to capture emails in Maildir format you can use
https://pypi.org/project/dsmtpd/, e.g.

.. code:: sh

   git clone git://github.com/matrixise/dsmtpd.git
   cd dsmtpd
   python3 -m dsmtpd -i localhost -p 8025 -d /path/to/Maildir

``/path/to/Maildir`` has to be either an existing
`Maildir <https://en.wikipedia.org/wiki/Maildir>`__ or non-existing, in
which case it will be created by dsmtpd.

You can access the Maildir with mutt, for example:

::

   mutt -f  /path/to/Maildir

Hint: By default ``Esc P`` will trigger mutt’s
``<check-traditional-pgp>``
`function <http://www.mutt.org/doc/manual/#reading-misc>`__, in case you
want to check a no-MIME signature.

Test Suite
----------

The test suite is split into two parts because some tests may fail
depending on hardware specs (execution time) and their failure would not
indicate errors per se.

The regular unit tests which must succeed can be started with
``make check``; to run the complete test suite, use ``make check_all``.

History
=======

The intelmq-mailgen file was initially copied from
https://github.com/certat/intelmq/blob/a29da5d798bd114535326ffdd2f5000c4b6a21e7/intelmq/bin/intelmqcli
(revision from 2016-03-08).

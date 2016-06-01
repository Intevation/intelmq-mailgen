IntelMQ MailGen
===============

IntelMQ command line tool to process events.

The intelmq-mailgen file was initially copied from
https://github.com/certat/intelmq/blob/a29da5d798bd114535326ffdd2f5000c4b6a21e7/intelmq/bin/intelmqcli (revision from 2016-03-08).

Installation
============

Dependencies
------------

 * https://bitbucket.org/bereiter/pyxarf (v==0.0.5bereiter)
 * (intelmq)
 * python3 (v>=3.2)

Database
--------

Create a new database named `intelmq-events` in the default cluster:

    createdb --encoding=UTF8 --template=template0 intelmq-events


Initialize the database:

    psql -f sql/events.sql intelmq-events
    psql -f sql/notifications.sql intelmq-events


The `notifications.sql` script creates two roles, on for each of the
main tasks in the event database: inserting new events (usually via
IntelMQ's postgres output bot) and sending notification mails (via
intelmq-mailgen). We need two conrete users that can be used to actually log
in and perform the task:

    # user for intelmq-mailgen:
    createuser --encrypted --pwprompt intelmq_mailgen
    psql -c "GRANT eventdb_send_notifications TO intelmq_mailgen" intelmq-events 

    # user for postgres output bot:
    createuser --encrypted --pwprompt intelmq
    psql -c "GRANT eventdb_insert TO intelmq" intelmq-events



Configuration
-------------

`intelmq-mailgen` currently searches for configuration files in two places:
`~/.intelmq/intelmq-mailgen.conf` and `/etc/intelmq/intelmq-mailgen.conf`.
Settings are read from both files with the one in `~` taking precedence.
The format for both files is the same. A complete example can be found
in `intelmq-mailgen.conf.example`.


Templates
---------

Templates for the emails should be in the directory named as
`template_dir` in the configuration file or a sub-directory thereof. The
first line of a template file is used as the subject line of the mails
sent by `intelmq-mailgen` and the rest of the lines as the body.

Security considerations
-----------------------
 * It is assumed that we need to protect against malicious external data coming 
to us via the database. 
 * We do not need (or can) protect against attacks with administration rights.
 * As our command will be able to run with and witout user interaction, 
we assume that only users with administration rights 
have access to the machine and are allowed to start the interactive variant.
 * The privat key material for signing will have no extra protection by passphrase, 
thus the system itself needs to be secured adequately. (This can include separating
to setup intelmq itself on a different machine with only access to fill the database.)


Testing
=======

An easy way to test the actual sending of emails, is to use Python's
`smtpd` module, running the `DebuggingServer`:

    python3 -m smtpd -d -n -c DebuggingServer localhost:8025 

Run Test-Suite
--------------
```
cd tests
python3 -m unittest
```

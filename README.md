Event Processor
===============

IntelMQ command line tool to process events.

The intelmq-mailgen file was initially copied from
https://github.com/certat/intelmq/blob/a29da5d798bd114535326ffdd2f5000c4b6a21e7/intelmq/bin/intelmqcli (revision from 2016-03-08).

Installation
============

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
	psql -c "GRANT eventdb_send_notifications TO intelmq_mailgen"

    # user for postgres output bot:
    createuser --encrypted --pwprompt intelmq
    psql -c "GRANT eventdb_insert TO intelmq"



Configuration
-------------

`intelmq-mailgen` currently requires configuration files in two places:
`~/.intelmq/intelmq-mailgen.conf` and `/etc/intelmq/intelmq-mailgen.conf`.
Settings are read from both files with the one in `~` taking precedence.
The format for both files is the same. A complete example can be found
in `config-example.json`.


Templates
---------

Templates for the emails should be in the directory named as
`template_dir` in the configuration file or a sub-directory thereof. The
first line of a template file is used as the subject line of the mails
sent by `intelmq-mailgen` and the rest of the lines as the body.


Testing
=======

An easy way to test the actual sending of emails, is to use Python's
`smtpd` module, running the `DebuggingServer`:

    python3 -m smtpd -d -n -c DebuggingServer localhost:8025 

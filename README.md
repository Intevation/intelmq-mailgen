Event Processor
===============

IntelMQ command line tool to process events.

The intelmqcli file was copied from
https://github.com/certat/intelmq/blob/master/intelmq/bin/intelmqcli
at revision a29da5d


Installation
============

Database
--------

Create a new database named `eventdb` in the default cluster:

    createdb --encoding=UTF8 --template=template0 eventdb


Initialize the database:

    psql -f sql/events.sql eventdb
    psql -f sql/notifications.sql eventdb


The `notifications.sql` script creates two roles, on for each of the
main tasks in the event database: inserting new events (usually via
IntelMQ's postgres output bot) and sending notification mails (via
intelmqcli). We need two conrete users that can be used to actually log
in and perform the task:

    # user for intelmqcli:
    createuser --encrypted --pwprompt intelmq_cli
	psql -c "GRANT eventdb_send_notifications TO intelmq_cli"

    # user for postgres output bot:
    createuser --encrypted --pwprompt intelmq_output
    psql -c "GRANT eventdb_insert TO intelmq_output"



Configuration
-------------

`intelmqcli` currently requires configuration files in two places:
`~/.intelmq/intelmqcli.conf` and `/etc/intelmq/intelmqcli.conf`.
Settings are read from both files with the one in `~` taking precedence.
The format for both files is the same. A complete example can be found
in `config-example.json`.


Templates
---------

Templates for the emails should be in the directory named as
`template_dir` in the configuration file or a sub-directory thereof. The
first line of a template file is used as the subject line of the mails
sent by `intelmqcli` and the rest of the lines as the body.


Testing
=======

An easy way to test the actual sending of emails, is to use Python's
`smtpd` module, running the `DebuggingServer`:

    python3 -m smtpd -d -n -c DebuggingServer localhost:8025 

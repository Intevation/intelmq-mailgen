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
 * pygpgme (v>=0.3)
   * GnuPG (v>=2)

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

### OpenPGP Signatures
You need to set ```gnupg_home``` to a directory that is a home directory
for the version of GnuPG that you are using. It has to contain the
private and public key parts for the OpenPGP signature without
password protection.

For example the following lines will create a directory, 
check that it is fresh and import the testing key:

```
mkdir /tmp/gnupghome
chmod og-rwx /tmp/gnupghome
GNUPGHOME=/tmp/gnupghome gpg2 --list-secret-keys
GNUPGHOME=/tmp/gnupghome gpg2 --import src/intelmq-mailgen/tests/keys/test1.sec
```

Depending on your GnuPG version you may want to set additional options
for example using this line in ```$GNUPGHOME/gpg.conf``` to set the
default digest algorithm:
```
personal-digest-preferences SHA256
```

Now signing a file should work for your ```signing_key``` 
without asking for a passphrase, e.g.
```
echo Moin moin. | GNUPGHOME=/tmp/gnupghome gpg2 --clearsign --local-user "5F503EFAC8C89323D54C252591B8CD7E15925678"
```


Templates
---------

Templates for the emails should be in the directory named as
`template_dir` in the configuration file or a sub-directory thereof. The
first line of a template file is used as the subject line of the mails
sent by `intelmq-mailgen` and the rest of the lines as the body. The
body may optionally be separated from the subject line by one or more
empty lines.

The body text may allow some substitutions, depending on the format. For
instance, the CSV based formats replace `${events_as_csv}` with the CSV
formatted event data.

Specific Templates
------------------
A template which will be elaborated for more specific templates is called
`specific.txt` this template has to exist in the template directory.


Security considerations
-----------------------
 * It is assumed that we need to protect against malicious external 
data coming 
to us via the database. 
 * We do not need (or can) protect against local attacks with administration rights.
 * As our command will be able to run with and witout user interaction, 
we assume that only users with administration rights 
have access to the machine and are allowed to start the interactive variant.
 * The privat key material for signing will have 
no extra protection by passphrase, thus the system itself 
needs to be secured adequately. (This can include separating
to setup intelmq itself on a different machine with only access 
to fill the database.)
* We should pay attention preventing that the complete system 
becomes an effective signature (or encryption) oracle. 
To explain: Consider an attacker who will receive an automatic notification 
from our system. If this attacker also can trigger a warning over 
an used feed, she may partly control which plaintext is to be signed 
(or somewhere encrypted) and get the automated result. There is a small
potential that this may be used for an adaptive-plaintext attack 
under some circumstances.


Column Names
------------

It is possible to define Names for the CSV-Columns in code. This can be
achieved by altering the appropriate formatter. For instance
`mail_format_botnet_drone_as_csv` calls `mail_format_as_csv` as with a
list of pairs as the last parameter, one pair for each column. Each pair
consists of the IntelMQ-internal identifier and the column title.



Testing
=======

An easy way to test the actual sending of emails, is to use Python's
`smtpd` module, running the `DebuggingServer`:

    python3 -m smtpd -d -n -c DebuggingServer localhost:8025 

(Don't forget to configure the corresponding
smtp host and port in your config.)

If you want to capture the emails in maildir format you can use
https://pypi.python.org/pypi/dsmtpd/0.2.2, e.g. like
```sh
git clone https://github.com/bernhardreiter/dsmtpd.git
cd dsmtpd
# now you need to have python3-docopt installed
# or drop docopt.py in from https://github.com/docopt/docopt
python3 -c 'from dsmtpd._dsmtpd import *; main()' -i localhost -p 8025 -d /path/to/Maildir
```

`Maildir` has to be either an existing email storage directory in 
[Maildir format](https://en.wikipedia.org/wiki/Maildir) or non-existing,
it which case it will be created by dsmtpd.

You can access a Maildir storage with several mail clients, e.g for mutt:
```
mutt -f  /path/to/Maildir
```
Hint: By default `Esc P` will trigger mutt's `<check-traditional-pgp>`
[function](http://www.mutt.org/doc/manual/#reading-misc), in case you
want to check a no-mime signature.


Run Test Suite
--------------

The test suite is split into two parts because some tests may fail depending on
hardware specs (execution time) and their failure would not indicate errors per
se.

The regular unit tests which must succeed can be started with ``make check``;
to run the complete test suite, use ``make check_all``.


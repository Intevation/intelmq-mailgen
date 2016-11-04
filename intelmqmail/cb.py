#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command line tool to send notfications for intelmq events.


Copyright (C) 2016 by Bundesamt für Sicherheit in der Informationstechnik
Software engineering by Intevation GmbH

This program is Free Software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Authors:
    Bernhard Herzog <bernhard.herzog@intevation.de>
    Roland Geider <roland.geider@intevation.de>
    Bernhard E. Reiter <bernhard@intevation.de>

    and others.

Based upon intelmqcli
https://github.com/certat/intelmq/blob/master/intelmq/bin/intelmqcli.py


Requires at least Python 3.2 because of DictWriter.writeheader()
"""

import smtplib
import argparse
import json
import locale
import logging
import os

import gpgme  # developed for pygpgme 0.3
from psycopg2.extras import RealDictConnection


from intelmqmail.templates import read_template
from intelmqmail.tableformat import format_as_csv
from intelmqmail.db import open_db_connection, get_pending_notifications, \
     load_events, new_ticket_number, mark_as_sent
from intelmqmail.mail import create_mail, clearsign
from intelmqmail.script import load_scripts


logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s - %(message)s')
log = logging.getLogger('intelmq-mailgen')
log.setLevel(logging.INFO)  # defaults to WARNING
#log.setLevel(logging.DEBUG)  # defaults to WARNING

if locale.getpreferredencoding() != 'UTF-8':
    log.critical(
        'The preferred encoding of your locale setting is not UTF-8'
        ' but "{}". Exiting.'.format(locale.getpreferredencoding()))
    exit(1)

APPNAME = "intelmqcbmail"
DESCRIPTION = """
"""

EPILOG = """
Searches for all unprocessed notifications and sends them.
"""

USAGE = """
    {appname}
    {appname} --all
""".format(appname=APPNAME)


def read_configuration():
    """Read configuration from user and system settings.
    The return value is a dictionary containing the merged settings read
    from the configuration files.
    """
    # Construct a single configuration dictionary with the contents of
    # the different conf files
    home = os.path.expanduser("~")  # needed for OSX
    user_conf_file = os.path.expanduser(home +
                                        '/.intelmq/intelmq-mailgen.conf')
    sys_conf_file = os.path.expanduser('/etc/intelmq/intelmq-mailgen.conf')
    if os.path.isfile(user_conf_file):
        with open(user_conf_file) \
             as conf_handle:
            user_config = json.load(conf_handle)
    else:
        user_config = dict()
    if os.path.isfile(sys_conf_file):
        with open(sys_conf_file) as conf_handle:
            system_config = json.load(conf_handle)
    else:
        system_config = dict()

    combined = system_config.copy()
    for key, value in user_config.items():
        if isinstance(combined.get(key), dict):
            combined[key].update(value)
        else:
            combined[key] = value

    if not combined:
        raise OSError("No configuration found.")

    return combined


def load_formats(config):
    formats = {}
    entry_points = load_scripts(config["script_directory"], "list_csv_formats")
    for entry in entry_points:
        formats.update(entry())
    return formats


def mail_format_as_csv(cur, directive, config, gpgme_ctx, format_spec):
    """Creates emails with csv attachment for given columns.

    Groups the events by 'source.asn' and creates an email for each.
    TODO: Assumes that all events have such a value.

    :returns: list of tuples (email object, list of notification ids, ticket)
    :rtype: list
    """
    events = load_events(cur, directive["event_ids"],
                         ["id"] + format_spec.event_table_columns())

    events_as_csv = format_as_csv(format_spec, events)

    subject_template, body_template = read_template(config["template_dir"],
                                                    directive["template_name"])

    asn = events[0]["source.asn"]
    ticket = new_ticket_number(cur)

    subject = subject_template.substitute(asn=asn, ticket_number=ticket)
    body = body_template.substitute(events_as_csv=events_as_csv,
                                    asn=asn, ticket_number=ticket)

    if gpgme_ctx:
        body = clearsign(gpgme_ctx, body)

    mail = create_mail(sender=config["sender"],
                       recipient=directive["recipient_address"],
                       subject=subject, body=body,
                       attachments=[])
    return [(mail, directive["directive_ids"], ticket)]


def create_mails(cur, directive, config, formats, gpgme_ctx):
    """Creates emails with events data in CSV format.

    :returns: list of tuples (email object, list of ids, ticket)
    :rtype: list
    """
    format_spec = formats.get(directive["event_data_format"])
    if format_spec is None:
        msg = ("Cannot generate emails for format %r"
               % (agg_notification["event_data_format"]))
        raise NotImplementedError(msg)

    return mail_format_as_csv(cur, directive, config, gpgme_ctx, format_spec)



def send_notifications(config, directives, cur, formats):
    """
    Create and send notification mails for all items in directives.

    All notifications that were successfully sent are marked as sent in
    the database. This function tries to make sure that this information
    can be committed as part of the transaction in progress even if
    errors occur during SQL statements executed by this function. The
    caller should also catch exceptions thrown by this method and always
    commit the transaction.

    :param config script configuration
    :param directives a list of aggregated_directives
    :param cur database cursor to use when loading event information

    :returns: number of send mails
    :rtype: int
    """
    sent_mails = 0
    gpgme_ctx = None

    if config["openpgp"]["always_sign"]:
        gpgme_ctx = gpgme.Context()
        signing_key = gpgme_ctx.get_key(config["openpgp"]["signing_key"])
        gpgme_ctx.signers = [signing_key]

    with smtplib.SMTP(host=config["smtp"]["host"],
                      port=config["smtp"]["port"]) as smtp:
        for directive in directives:
            cur.execute("SAVEPOINT sendmail;")
            try:
                try:
                    email_tuples = create_mails(cur, directive, config, formats,
                                                gpgme_ctx)

                    if len(email_tuples) < 1:
                        # TODO maybe use a user defined exception here?
                        raise RuntimeError("No emails for sending were generated!")
                except Exception:
                    log.exception("Could not create mails for %r."
                                  " Continuing with other notifications.",
                                  directive)
                else:
                    for email_tuple in email_tuples:
                        smtp.send_message(email_tuple[0])
                        mark_as_sent(cur, email_tuple[1], email_tuple[2])
                        sent_mails += 1

            except:
                cur.execute("ROLLBACK TO SAVEPOINT sendmail;")
                raise
            finally:
                cur.execute("RELEASE SAVEPOINT sendmail;")
    return sent_mails


def generate_notifications_interactively(config, cur, directives, formats):
    batch_size = 10

    pending = directives[:]
    while pending:
        batch, pending = pending[:batch_size], pending[batch_size:]
        print('Current batch (%d of %d total):'
              % (len(batch), len(batch) + len(pending)))
        for i in batch:
            print('    * {0} {1} ({2}): {3} events'
                  .format(i["recipient_address"],
                          i["template_name"],
                          i["event_data_format"],
                          len(i["event_ids"])))
        valid_answers = ("c", "s", "a", "q")
        while True:
            answer = input("Options: [c]ontinue, "
                           "[s]end this batch, "
                           "send [a]ll, "
                           "[q]uit? ").strip()
            if answer not in valid_answers:
                print("Please enter one of the characters %s"
                      % ", ".join(valid_answers))
            else:
                break
        if answer == "c":
            print("Skipping this batch.")
            pass
        elif answer == "q":
            print("Exiting without sending any further mails.")
            pending = []
        else:
            to_send = batch
            if answer == "a":
                to_send.extend(pending)
                pending = []

            print("Sending mails for %d entries... " % (len(to_send),))
            sent_mails = send_notifications(config, to_send, cur, formats)
            print("%d mails sent. " % (sent_mails,))


def mailgen(args, config, formats):
    cur = None
    conn = open_db_connection(config, connection_factory=RealDictConnection)
    try:
        cur = conn.cursor()
        cur.execute("SET TIME ZONE 'UTC';")
        directives = get_pending_notifications(cur)
        if directives == None:
            return
        if len(directives) == 0:
            log.info("No pending notifications to be sent")
            return

        if args.all:
            sent_mails = send_notifications(config, directives, cur, formats)
            log.info("{:d} mails sent.".format(sent_mails))
        else:
            generate_notifications_interactively(config, cur, directives,
                                                 formats)

    finally:
        if cur is not None:
            cur.close()
        # the only change to the database is marking the sent mails as
        # actually sent. We always want to commit that information even
        # when errors occur, so we're calling commit in the finally
        # block.
        conn.commit()
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        prog=APPNAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage=USAGE,
        description=DESCRIPTION,
        epilog=EPILOG,
        )
    parser.add_argument('-a', '--all', action='store_true',
                        help='Process all events (batch mode)')
    args = parser.parse_args()

    config = read_configuration()

    # checking openpgp config
    if "openpgp" not in config or {
            "always_sign", "gnupg_home", "signing_key"
            } != config["openpgp"].keys():
        log.critical("Config section openpgp missing or incomplete. Exiting.")
        exit(1)
    # setting up gnupg
    os.environ['GNUPGHOME'] = config["openpgp"]["gnupg_home"]


    formats = load_formats(config)

    mailgen(args, config, formats)

# to lower the chance of problems like
# http://python-notes.curiousefficiency.org/en/latest/python_concepts/import_traps.html#the-double-import-trap
# we discourage calling this file directly as a "script", instead use
# the entry-point script by the temporary install or
# go to the right toplevel directory and use a full import like
#  python3 -c "from intelmqmail import cb; cb.main()"


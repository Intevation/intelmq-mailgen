"""Command line tool to send notifications for intelmq events.

Copyright (C) 2016, 2021 by Bundesamt für Sicherheit in der Informationstechnik
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
import sys
from typing import Dict, Union, List

import gpg
from psycopg2.extras import RealDictConnection
from psycopg2.extensions import connection as psycopg2_connection


from intelmqmail.db import open_db_connection, get_pending_notifications
from intelmqmail.script import load_scripts
from intelmqmail.notification import Directive, SendContext, ScriptContext, \
    Postponed
from intelmqmail.templates import Template

from typing import Optional


logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


if locale.getpreferredencoding() != 'UTF-8':
    log.critical(
        'The preferred encoding of your locale setting is not UTF-8'
        ' but %r. Exiting.', locale.getpreferredencoding())
    sys.exit(1)

APPNAME = "intelmqcbmail"
DESCRIPTION = """
Searches for all unprocessed e-mail notifications and sends them.

Without --all, the program enters an interactive mode,
showing batches of 10 notifications and options to skip, sending
the batch or sending all pending notifications.
"""

EPILOG = """
The configuration is read from
~/.intelmq/intelmq-mailgen.conf (user configuration file) and
/etc/intelmq/intelmq-mailgen.conf (system configuration file)
If --config is given, the parameter file is used instead of the
system configuration file. The user configuration file is always active.

Documentation:
https://github.com/Intevation/intelmq-mailgen#readme
https://github.com/Intevation/intelmq-mailgen/blob/master/docs/concept.rst
"""

USAGE = """
    {appname}
    {appname} --all

""".format(appname=APPNAME)


def read_configuration(conf_file_path: Optional[str] = None):
    """Read configuration from user and system settings.
    The return value is a dictionary containing the merged settings read
    from the configuration files.

    Parameters:
        conf_file_path: The path to the system configuration file.
            The user configuration file is always used additionally.
            default: /etc/intelmq/intelmq-mailgen.conf
    """
    # Construct a single configuration dictionary with the contents of
    # the different conf files
    home = os.path.expanduser("~")  # needed for OSX
    user_conf_file = os.path.expanduser(home +
                                        '/.intelmq/intelmq-mailgen.conf')
    if conf_file_path is None:
        conf_file_path = '/etc/intelmq/intelmq-mailgen.conf'
    sys_conf_file = os.path.expanduser(conf_file_path)
    if os.path.isfile(user_conf_file):
        with open(user_conf_file) as conf_handle:
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


def load_script_entry_points(config):
    return load_scripts(config["script_directory"], "create_notifications",
                        logger=log)


def create_notifications(cur, directive, config, scripts, gpgme_ctx, template: Optional[Template] = None,
                         templates: Optional[Dict[str, Template]] = None):
    script_context = ScriptContext(config, cur, gpgme_ctx,
                                   Directive(**directive), log, template=template, templates=templates)
    for script in scripts:
        log.debug("Calling script %r", script.filename)
        try:
            notifications = script(script_context)
        except Exception:
            log.exception("Error while running entry point of script %r",
                          script.filename)
            continue
        else:
            log.debug("Script %r finished. Result: %r", script.filename, notifications)
        if notifications:
            return notifications
    raise NotImplementedError(f"Cannot generate emails for directive {directive!r}")


def send_notifications(config, directives, cur, scripts, template: Optional[Template] = None,
                       templates: Optional[Dict[str, Template]] = None,
                       dry_run: bool = False, get_preview: bool = False) -> Union[int, List[str]]:
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
    :param template
    :param templates
    :param dry_run if true, don't send the mail, rollback database changes
    :param get_preview return content of first email

    :returns: number of sent mails, or if get_preview is True a list of notifications
    """
    sent_mails = 0
    postponed = 0
    errors = 0
    gpgme_ctx = None

    if config["openpgp"]["always_sign"]:
        gpgme_ctx = gpg.Context()
        signing_key = gpgme_ctx.get_key(config["openpgp"]["signing_key"])
        gpgme_ctx.signers = [signing_key]

    if get_preview:
        preview_notifications = []

    for directive in directives:
        # When processing a directive, we set a savepoint in the
        # database so that we can roll back to it if errors happen
        # and still retain and later commit the changes made for
        # directives processed earlier. For this to work, we have to
        # be careful when handling exceptions. Any exception that
        # could be an error, particularly exceptions that indicate a
        # problem with the database transaction must lead to a
        # "ROLLBACK TO SAVEPOINT". Otherwise, if the transaction has
        # encountered an error, no statements other than rollbacks
        # will be accepted by the database and we would lose the
        # changes we want to commit.
        #
        # Among the changes we want to commit are the information
        # about the sent notifications and the ticket numbers,
        # including the daily reset of the ticket numbers. Not
        # committing this could lead to notifications being sent
        # twice and the same ticket numbers being reused for
        # different notifications.
        cur.execute("SAVEPOINT sendmail;")
        try:
            notifications = create_notifications(cur, directive, config,
                                                 scripts, gpgme_ctx, template=template, templates=templates)

            if not notifications:
                log.warning("No emails for sending were generated for %r!",
                            directive)
            elif notifications is Postponed:
                postponed += 1
            else:
                with smtplib.SMTP(host=config["smtp"]["host"],
                                  port=config["smtp"]["port"]) as smtp:
                    context = SendContext(cur, smtp)
                    for notification in notifications:
                        if get_preview:
                            preview_notifications.append(str(notification.email))
                        elif dry_run:
                            log.debug("Skip sending notification (to %r with subject %r) because of dry run.", notification.email.get('To'), notification.email.get('Subject'))
                        else:
                            notification.send(context)
                        sent_mails += 1
        except BaseException as exc:
            cur.execute("ROLLBACK TO SAVEPOINT sendmail;")
            # if it's a "normal" exception, assume that it's a
            # problem with the directive or the scripts that process
            # it. Simply try the next directives. If it's a not a
            # normal exception, e.g. if it's SystemExit or
            # KeyboardInterrupt, reraise the exception since it's
            # likely that
            if isinstance(exc, Exception):
                log.exception("Could not create or send mails for %r."
                              " Continuing with other notifications.",
                              directive)
                errors += 1
            else:
                raise
        finally:
            if dry_run or get_preview:
                cur.execute("ROLLBACK TO SAVEPOINT sendmail;")
            else:
                cur.execute("RELEASE SAVEPOINT sendmail;")
    if get_preview:
        return preview_notifications
    return (sent_mails, postponed, errors)


def generate_notifications_interactively(config, cur, directives, scripts, dry_run: bool = False):
    batch_size = 10

    pending = directives[:]
    while pending:
        batch, pending = pending[:batch_size], pending[batch_size:]
        print(f'Current batch ({len(batch)} of {len(batch) + len(pending)} total):')
        for i in batch:
            print(f'    * {i["recipient_address"]} {i["template_name"]} ({i["notification_format"]}/{i["event_data_format"]}): {len(i["event_ids"])} events')
        valid_answers = ("c", "s", "a", "q")
        while True:
            answer = input("Options: [c]ontinue (skip), "
                           "[s]end this batch, "
                           "send [a]ll, "
                           "[q]uit? ").strip()
            if answer not in valid_answers:
                print(f'Please enter one of the characters {", ".join(valid_answers)}')
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

            print(f"Sending mails for {len(to_send)} entries... ")
            sent_mails, postponed, errors = send_notifications(config, to_send, cur,
                                                               scripts, dry_run=dry_run)
            print(f"%s{sent_mails} mails sent, {postponed} postponed, {errors} errors." % ('Simulation: ' if dry_run else ''))


def mailgen(config: dict, scripts: list, process_all: bool = False, template: Optional[str] = None, templates: Optional[Dict[str, str]] = None,
            dry_run: bool = False, get_preview: bool = False, conn: Optional[psycopg2_connection] = None,
            additional_directive_where=Optional[str]) -> str:
    """
    Run mailgen either interactively (process_all=False) or non-interactively (process_all=True)

    Parameters:
        config
        scripts
        process_all: See above
        template: Fallback template as string, optional
        templates: Dictionary of templates with items name: body, optional. Overrides any template files in the template directory
        dry_run: If true, rollbacks at the end
        get_preview: Returns the result of the first send_notifications call
        conn: Database connection, optional
        additional_directive_where: Additional WHERE selector for the directives. If not given, use the one from the config. Details see docs.
    """
    if dry_run:
        log.info("Running dry-run mode. Not sending mails and not writing changes to the database. Simulation only.")
    cur = None
    if not conn:
        log.debug("Opening database connection")
        conn = open_db_connection(config, connection_factory=RealDictConnection)
    if not additional_directive_where:
        additional_directive_where = config['database'].get('additional_directive_where')

    result = None
    if template:
        # convert string template to Template object
        template = template.strip()
        subject = template[:template.find('\n')]  # first line
        body = template[template.find('\n') + 1:] + '\n'  # rest plus trailing newline
        template = Template.from_strings(subject, body)
    if templates:
        for template_name in templates:
            # convert string template to Template object
            template = templates[template_name].strip()
            subject = template[:template.find('\n')]  # first line
            body = template[template.find('\n') + 1:] + '\n'  # rest plus trailing newline
            templates[template_name] = Template.from_strings(subject, body)

    try:
        cur = conn.cursor()
        cur.execute("SET TIME ZONE 'UTC';")
        log.debug("Fetching pending directives")
        directives = get_pending_notifications(cur,
                                               additional_directive_where=additional_directive_where)
        if directives is None:
            # This case has been logged by get_pending_notifications.
            return [] if get_preview else "No directives"
        if len(directives) == 0:
            log.info("No pending notifications to be sent")
            return [] if get_preview else "No pending notifications to be sent"

        log.debug("Got %d groups of directives", len(directives))

        if process_all:
            log.debug("Start processing directives")
            if get_preview:
                return send_notifications(config, directives, cur, scripts, template, templates, dry_run=dry_run, get_preview=get_preview)
            sent_mails, postponed, errors = send_notifications(config, directives, cur,
                                                               scripts, template, templates, dry_run=dry_run)
            result = f"%s{sent_mails} mails sent, {postponed} postponed, {errors} errors." % ('Simulation: ' if dry_run else '')
            log.info(result)
        else:
            generate_notifications_interactively(config, cur, directives,
                                                 scripts, dry_run=dry_run)

    except:
        raise
    finally:
        if cur is not None:
            cur.close()

        if dry_run:
            conn.rollback()
        else:
            # the only change to the database is marking the sent mails as
            # actually sent. We always want to commit that information even
            # when errors occur, so we're calling commit in the finally
            # block.
            conn.commit()
        conn.close()

    if result:
        return result


def main():
    """
    Start mailgen interactively, parsing command line args
    """
    parser = argparse.ArgumentParser(
        prog=APPNAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage=USAGE,
        description=DESCRIPTION,
        epilog=EPILOG,
    )
    parser.add_argument('-a', '--all', action='store_true',
                        help='Process all events (batch mode) non-interactively')
    parser.add_argument('-c', '--config',
                        help='Alternative system configuration file')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Activate verbose debug logging')
    parser.add_argument('-n', '--dry-run', action='store_true',
                        help='Dry run. Simulate only.')
    args = parser.parse_args()

    config = read_configuration(conf_file_path=args.config)

    # Set the logLevel for all submodules
    module_logger = logging.getLogger(__name__.rsplit(sep=".", maxsplit=1)[0])
    # using INFO as default, otherwise it's WARNING
    module_logger.setLevel(config.get("logging_level", "INFO"))
    if args.verbose:
        log.setLevel(logging.DEBUG)

    start(config, process_all=args.all, dry_run=args.dry_run)


def start(config: dict, process_all=False, template: Optional[str] = None, templates: Optional[Dict[str, str]] = None,
          dry_run: bool = False, get_preview: bool = False, conn: Optional[psycopg2_connection] = None,
          additional_directive_where: Optional[str] = None) -> str:
    """
    Start mailgen
    can be used by other programs
    """
    # checking openpgp config
    if "openpgp" not in config or {
            "always_sign", "gnupg_home", "signing_key"
    } != config["openpgp"].keys():
        log.critical("Config section openpgp missing or incomplete. Exiting.")
        sys.exit(1)
    # setting up gnupg
    os.environ['GNUPGHOME'] = config["openpgp"]["gnupg_home"]

    scripts = load_script_entry_points(config)
    if not scripts:
        log.error("Could not load any scripts from %r",
                  config["script_directory"])
        sys.exit(1)

    return mailgen(config, scripts, process_all=process_all, template=template, templates=templates, dry_run=dry_run,
                   get_preview=get_preview, conn=conn, additional_directive_where=additional_directive_where)


# to lower the chance of problems like
# http://python-notes.curiousefficiency.org/en/latest/python_concepts/import_traps.html#the-double-import-trap
# we discourage calling this file directly as a "script", instead use
# the entry-point script by the temporary install or
# go to the right toplevel directory and use a full import like
#  python3 -c "from intelmqmail import cb; cb.main()"

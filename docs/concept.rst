Handling notifications with IntelMQ Mailgen
===========================================

Overview
--------

When sending notifications based on the events processed by IntelMQ, the
system---consisting of both IntelMQ and Mailgen---has to decide for each
event who is to be notified when about the event and in which way. This
information is represented by a `notification directive` that contains
all the information needed for sending the notifications for an event.
IntelMQ Mailgen processes these directives and sends mails accordingly.

The directives are created by the IntelMQ side of the system. Expert
bots in IntelMQ read contact information from a database (the CERT-bund
Contact Database bot) and decide based on that information and the other
event data which directives to create for an individual event (the
CERT-bund Contact Rules bot). The directives are then written to the
event database by IntelMQ's ``postgresql`` output bot automatically as
part of the event data.

IntelMQ Mailgen reads the directives that have not yet been processed
from the database, aggregates them when possible, and generates and
sends mails when the time has come. When mails are sent, the sending
time and some other information such as the ticket number is stored in
the database, indicating that the directive has been processed and to
allow any questions the recipients of the mails may have to be linked to
the events the notification was about.

Both the rules expert bot and Mailgen can be configured with python
scripts that are run for all events and directives respectively.

The rest of this part of the document describes this in more detail.


Notification Directives
-----------------------

A `notification directive` describes one notification for one event.
There may be zero or more directives for each event, though. It's
meaning is something like "Send a mail to foo@example.com using template
T once a day and include the event data as CSV". This meaning is encoded
in the attributes listed in the next section. The precise meaning is
ultimately up to conventions used by both the scripts in the rule expert
bot which generate the directives and the scripts in mailgen which
interpret them.

Mailgen can aggregate directives, that is it can process directives for
different events as if it were one directive for all those events, if
the directives are similar enough. Two directives are considered similar
enough in this sense when most of their attributes are equal. For
instance, the address of the recipient, the data format and the template
must be equal, otherwise it would not make sense to aggregate them at
all. There are some other considerations, see :ref:`aggregation` for
details.


Attributes
..........

A directive contains the following information (the names of these
attributes are the actual identifiers used in the code):

    :recipient_address: The email address of the recipient.
    :notification_format: The main format of the notification.
    :template_name: The name of the template for the contents of the
                    notification.
    :event_data_format: The format to use for event data included in the
                        notification.
    :aggregate_identifier: Additional key/value pairs used when
			   aggregating directives. Both keys and values
			   are strings. (See also :ref:`aggregation`)
    :notification_interval: Interval between notifications for similar
			    events (see
			    :ref:`aggregation_and_notification_interval`)


The three attributes ``notification_format``, ``template_name`` and
``event_data_format`` are the main parameters that define the contents
of the generated mails. The ``notification_format`` is intended to name
the overall format of the mail and the template and data format specify
some of the details.

There's some other information related to directives once they're in the
event database:

    ``inserted_at``

        Date/Time when the directive was added to the event database.

    Event ID

        The ID in the event database of the event the directive belongs
        to.

    Ticket number

        A unique identifier included in notifications sent by mailgen
        that can be used to identify which directives (and therefore
        which events) were included in a particular notification that a
        recipient may have questions about.

        The ticket number is generated when mailgen actually generates a
        mail for a given directive.

    Sent At

        Date/time when the notification was sent.



.. _aggregation:

Aggregation
...........

For two directives to be considered similar enough to be aggregated, all
of these attributes must be equal:

    * ``recipient_address``
    * ``template_name``
    * ``notification_format``
    * ``event_data_format``
    * ``aggregate_identifier``

That the first four of these must be equal is obvious enough. They
directly influence the contents of the mails. The aggregate identifier
is a collection of key/value pairs that can be used by the rule in the
rule expert bot to further control how directives are aggregated. For
example, you could aggregate directives for events with the same
``classification.type``. The key/value pairs are available in the
mailgen scripts when the directive are processed and can be referenced
in templates.


.. _aggregation_and_notification_intervals:

Aggregation only makes sense if directives are not processed immediately
in order to let directives accumulate for a while. The main parameter in
a directive that can be used to control this is the
``notification_interval`` attribute which holds the minimum duration
between to similar notifications, where similar means exactly the same
thing as for aggregation. How this is interpreted exactly, and whether
this or some other criterion is used, is up to the scripts in mailgen,
however.


Mailgen
-------

Mailgen reads directives from the event database, processes them and
sends mail. In particular, it performs these steps:

 1. Load the scripts from the script directory (see :ref:`mailgen_scripts`)

 2. Read the aggregated pending directives from the database

 3. For each group of directives, perform the following steps:

    1. call each script and if one of the scripts generates a message,
       stop processing (see :ref:`mailgen_scripts`)

    2. Send the messages

    3. Mark the messages as sent in the database, recording the
       date/time when the message was sent.

`Pending directives` are the directives for which no mail has been sent
yet. Aggregation is done according to the criteria described in
:ref:`aggregation`.

For each group of directives some more attributes are read from the
database in addition to the attributes that were used for aggregation:

    :last_sent: When the last similar mail was sent (see
		:ref:`aggregation_and_notification_interval`)
    :inserted_at: When the newest of the directives in the group was
                  added to the database.
    :event_ids: A list with the database IDs of all the events whose
                directives have been accumulated in the group
    :directive_ids: A list with the database IDs of all the directives
                    that have been accumulated in the group
    :notification_interval: The longest of the ``notification_interval``
                            values of all the directives in the group.



.. _mailgen_scripts:

Mailgen Scripts
...............

Most of the logic for handling the directives is implemented with python
scripts, like the examples in the ``example_scripts/`` subdirectory.
When mailgen is started it reads all the python files in the configured
script directory that have names starting with two decimal digits.

Each of the scripts must define a function called
``create_notifications``. Mailgen calls this function with a ``Context``
object as parameter which provides access to the group of directives
being processed (see the doc-strings in
``intelmqmail/notification.py``). The function is expected to return one
of three possible results:

    ``None``

        Indicates that the script is not interested in processing the
        directive.

    A list of ``EmailNotification`` objects

        Each of these objects represents a complete email that has not
        been sent yet. Typically the script uses helper methods on the
        context object to create these, like ``mail_format_as_csv`` (see
        the doc-strings for details)

    ``Postponed``

        A predefined constant in the ``intelmqmail.notification``
	module. This constant indicates that the script would handle the
	directive if sufficient time has passed. For instance, it may
	return this constant the time that passed since the
	``last_sent`` date is shorter than the
	``notification_interval``.


When mailgen processes a group of directives, it calls the
``create_notifications`` function of each of the scripts in turn in
alphabetical order of the script name (hence the two leading digits that
provide a simple way to order the scripts). Mailgen stops once one of
the functions returns something other than None. If the return value is a
list of ``EmailNotification`` objects, mailgen sends those mails as
described in :ref:`mailgen_sending_mails`.




Contact-DB Bot
--------------

On the other end of the notification processing is the `Contact-DB bot`.
This expert bot in IntelMQ reads contact information from the contact
database and adds it to the event. This is done twice, once for contacts
related to the source of the event and once for the destination,
yielding two sets of contact information. Each set uses these types of
data:

    matches

        These describe which parts of the event matched some entry in
        the database. This is the field name without the `source.` or
        `destination.` prefix and the ID of the organisation it belongs
        to. For network matches it also contains the network address
        because in this case the field does not contain the same
        information because a match means that the IP address in the
        event is contained in the network.

    organisations

        An organisation links the matches with the actual contact
        information.

    contacts

        An actual contact which is mostly just an email address.

    annotations

        Matches, organisation and contacts may have any number of
        annotations. Annotations have a tag (just a string) and an
        optional condition. The condition is a simple comparison of an
        event field with a constant. The idea is that the annotation
        should only be used to make decisions about notifications when
        the condition is true.



Rule-Expert Bot
---------------

This expert bot makes the decisions about the notifications. It takes an
event with contact information added by the contact db bot and generates
directives based on that contact information and the event data.

In order to be flexible this bot uses python scripts in very much the
same way as mailgen. In the rule expert bot, the function is called
`determine_directives` and like in mailgen gets a context object as
parameter. The class is different, of course, this time it's `Context`
in `intelmq.bots.experts.certbund_contact.rulesupport`. The context
object provides access to the event data and the contact information.
The script should examine the information and depending on what it
finds, create directives and add them to the context. The return value
of the `determine_directives` function is a boolean. Returning true
means that no further scripts should be executed.

There are some example scripts in
`intelmq/bots/experts/certbund_contact/example-rules/` which demonstrate
how to write such scripts.

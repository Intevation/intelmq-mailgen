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
allow any questions the recipents of the mails may have to be linked to
the events the notification was about.

Both the rules expert bot and Mailgen can be configured with python
scripts that are run for all events and directives respectively.

The rest of this part of the document describes this in more detail.


Notification Directives and Mailgen
-----------------------------------

A `notification directive` describes one notification for one event
(there may be zero or more directives for each event) and contains the
following information:

    :recipient_address: The email address of the recipient.
    :template_name: The name of the template for the contents of the
                    notification.
    :notification_format: The main format of the notification.
    :event_data_format: The format to use for event data included in the
                        notification.
    :aggregate_identifier: Additional key/value pairs used when
			   aggregating directives. Both keys and values
			   are strings.
    :notification_interval: Interval between notifications for similar
			    events. Can be used together with last_sent
			    to determine whether this interval has
			    expired.

All of these attributes except for the notification interval are
considered when aggregating directives. Two directives with equal values
for these fields will be processed together, so that they could be sent
as a single mail.



Contact-DB Bot
--------------


Rule-Expert Bot
---------------

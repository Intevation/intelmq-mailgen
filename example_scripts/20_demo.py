"""
SPDX-FileCopyrightText: 2025-2026 Institute for Common Good Technology

SPDX-License-Identifier: AGPL-3.0-or-later
"""
from datetime import date

from intelmqmail.notification import Postponed


def create_notifications(context):
    if context.directive.notification_format != 'demo':
        context.logger.debug("Notification format is not 'demo', but %r.", context.directive.notification_format)
        return None

    return context.mail_format_as_csv(substitutions=context.substitutions,
                                      attach_event_data=True)

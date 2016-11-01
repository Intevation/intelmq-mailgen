# Copyright (C) 2016 by Bundesamt für Sicherheit in der Informationstechnik
# Software engineering by Intevation GmbH
#
# This program is Free Software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Basic support for tabular data formats such as CSV"""


import json


class FeedSpecificFormat:

    """Describe a feed-specific CSV format.
    """

    def __init__(self, feed_name, columns):
        """Initialize the format specification.
        The columns parameter should be a list of Column instances."""
        self.feed_name = feed_name
        self.columns = columns

    def column_titles(self):
        """Return a dictionary with the column titles for use a CSV header."""
        return dict((col.csv_column_key, col.title) for col in self.columns)

    def event_table_columns(self):
        """Return a list with the columns to retrieve from the event table.
        """
        return list(set(col.event_table_column for col in self.columns))

    def csv_column_keys(self):
        """Return a list with the keys used for the CSV rows.
        The list is to be used as the field names parameter for the
        csv.DictWriter class and matches the dictionaries returned by the
        csv_row_from_event method.
        """
        return [col.csv_column_key for col in self.columns]

    def csv_row_from_event(self, event):
        """Return the csv row for one given event."""
        return dict((col.csv_column_key, col.csv_value_from_event(event))
                    for col in self.columns)



class Column:

    """Specifies a single column for CSV output.

    This base class only provides a title for the column.

    Derived classes should implement the following attributes and methods:

    :title: the column title
    :event_table_column: the column of the event table to retrieve
    :csv_column_key: a key to use for the CSV row dictionary.
        All columns of a single format must have different
        csv_column_key values.
    :csv_value_from_event(event): Return the value of the column for the
        given event. The event parameter is a dictionary that has at
        least a value for the event_table_column.
    """

    def __init__(self, title):
        self.title = title


class IntelMQColumn(Column):

    """CSV Column filled directly from an IntelMQ field."""

    def __init__(self, title, field_name):
        super(IntelMQColumn, self).__init__(title)
        self.field_name = field_name

    @property
    def event_table_column(self):
        return self.field_name

    @property
    def csv_column_key(self):
        return self.field_name

    def csv_value_from_event(self, event):
        return event[self.field_name]


class ExtraColumn(Column):

    """CSV Column filled with a value taken from the IntelMQ extra field.

    The extra_key parameter of the constructor gives the name key to
    look up in the JSON dictionary contained in the extra field.
    """

    def __init__(self, title, extra_key):
        super(ExtraColumn, self).__init__(title)
        self.extra_key = extra_key

    @property
    def event_table_column(self):
        return "extra"

    @property
    def csv_column_key(self):
        return "extra:" + self.extra_key

    def csv_value_from_event(self, event):
        value = event[self.event_table_column]
        if isinstance(value, str):
            # With psycopg 2.4.5 values of type JSON in the database are
            # returned as strings. In newer psycopg versions they are
            # converted automatically, so we may not have to convert the
            # value.
            # FIXME: This aspect (not having to convert with newer psycopg
            # versions) has not been tested.
            value = json.loads(value)
        return value.get(self.extra_key)



# convenience functions for building the format datastructures in a more
# declarative way.

def build_feed_specific_formats(formats):
    """Return a dictionary mapping format names to format specifications.
    The parameter is a list of (formatname, columns) pairs, where
    formatname is the name of the format as a string and columns is a
    list of column specifications. The formatname values are used as the
    keys in the dictionary and both formatname and columns are passed to
    build_feed_specific_format to create the corresponding format
    specification.
    """
    return dict((name, build_feed_specific_format(name, columns))
                for name, columns in formats)

def build_feed_specific_format(feed_name, columns):
    """Build a FeedSpecificFormat instance for feed_name.
    The columns parameter should be a list of column specifications
    which are passed to build_feed_specific_column to create the list of
    columns for the FeedSpecificFormat instance.
    """
    return FeedSpecificFormat(feed_name,
                              [build_feed_specific_column(col)
                               for col in columns])

def build_feed_specific_column(col):
    """Return a Column instance built from a column specification.
    A column specification may either be a tuple of the form
    (intelmq_field, column_title) in which case an IntelMQColumn is
    created from these parameters or an instance of Column which is
    returned as is.
    """
    if isinstance(col, tuple):
        intelmq_field, column_title = col
        return IntelMQColumn(column_title, intelmq_field)
    else:
        return col

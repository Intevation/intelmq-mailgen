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

"""Template handling"""


import os
import string


def full_template_filename(template_dir, template_name):
    """Return the full absolute file name of a template.

    The template_name parameter is interpreted relative to template_dir
    and must refer to a file under that directory. If the resulting file
    name would name a file outside of template_dir, a ValueError
    exception is raised. This check is done to guard against malicious
    template names.
    """
    # make sure absbase ends with "/" so that the check whether the
    # resulting template file name is located under template_dir
    # actually works. os.path.abspath will remove any trailing slashes
    # from its parameter so we can simply append a single one.
    absbase = os.path.abspath(template_dir) + os.path.sep
    absfilename = os.path.abspath(os.path.join(template_dir, template_name))
    if not absfilename.startswith(absbase):
        raise ValueError(f"Invalid template name {template_name!r}! Full template filename"
                         f" would be outside of the template base directory {template_dir!r}.")
    return absfilename


def read_template(template_dir, template_name):
    """Read the email template indicated by template_dir and template_name.

    The name of the template file is determined with full_template_filename.

    File Format:

      - The first non-empty line of the file is assumed to be the
        template string for the subject line of the email.

      - The rest of the lines are the email body. Leading and trailing
        white space is removed from the body and a newline added at the
        end. This allows e.g. an empty line in the template between the
        subject line and the body.

        The resulting string is used as template string in a Python
        Template object, thus allowing some simple substitutions. See
        the different formatter implementations for the substitutions they
        support.

    The return value is an instance of the Template class.
    """
    with open(full_template_filename(template_dir, template_name)) as infile:
        subject = None
        while not subject:
            subject = infile.readline().strip()
        return Template.from_strings(subject, infile.read().strip() + "\n")


class IntelMQStringTemplate(string.Template):

    """Variant of string.Template that allows '.' characters in identifiers."""

    idpattern = "[_a-z][_a-z0-9.]*"


class Template:

    """A template for email contents.

    The template contains two separate templates, one for the subject
    and one for the body. To fill in values, use the substitute()
    method.
    """

    def __init__(self, subject, body):
        """Initialize the template with subject and body.
        Both parameters should behave like string.Template instances.
        """
        self.subject = subject
        self.body = body

    @classmethod
    def from_strings(cls, subject, body):
        """Convenience method that creates a template from strings.
        The strings are converted to templates with IntelMQStringTemplate.
        """
        return cls(IntelMQStringTemplate(subject),
                   IntelMQStringTemplate(body))

    def __repr__(self):
        return f"Template({self.subject!r}, {self.body!r})"

    def substitute(self, substitutions):
        """Fill-in the template with the given substitutions.

        The substitutions parameter should be a dictionary mapping the
        keys that might be in the template to the respective values.
        This is done by passing the dictionary to the subject/body's
        substitute method.

        The return value is a pair (subject, body) with the filled in
        subject and body.
        """
        return (self.subject.substitute(substitutions),
                self.body.substitute(substitutions))

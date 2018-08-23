"""Load user supplied scripts"""

import os
import glob

import logging


log = logging.getLogger(__name__)


class Script:

    """Represents a script or plugin.

    The script can be run by simply calling the Script object. All
    parameters will be forwarded to the actual entry point and its
    return value will be returned.

    The public attribute filename is the name of the python file the
    script was loaded from.
    """

    def __init__(self, filename, entry_point):
        self.filename = filename
        self.entry_point = entry_point

    def __call__(self, *args, **kw):
        return self.entry_point(*args, **kw)


def load_scripts(script_directory, entry_point, logger=None):
    if logger is None:
        logger = log
    entry_points = []
    found_errors = False
    glob_pattern = os.path.join(glob.escape(script_directory),
                                "[0-9][0-9]*.py")
    for filename in sorted(glob.glob(glob_pattern)):
        try:
            with open(filename, "r") as scriptfile:
                my_globals = {}
                exec(compile(scriptfile.read(), filename, "exec"),
                     my_globals)
                entry = my_globals.get(entry_point)
                if entry is not None:
                    entry_points.append(Script(filename, entry))
                else:
                    found_errors = True
                    logger.error("Cannot find entry point %r in %r",
                                 entry_point, filename)
        except Exception:
            found_errors = True
            logger.exception("Exception while trying to find entry point %r in %r",
                             entry_point, filename)
    if found_errors:
        raise RuntimeError("Errors found while loading scripts."
                           " See log file for details")
    return entry_points

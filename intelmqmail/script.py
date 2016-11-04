"""Load user supplied scripts"""

import os
import glob

import logging


log = logging.getLogger(__name__)


def load_scripts(script_directory, entry_point):
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
                    entry_points.append(entry)
                else:
                    found_errors = True
                    log.error("Cannot find entry point %r in %r",
                              entry_point, filename)
        except Exception:
            found_errors = True
            log.exception("Exception while trying to find entry point %r in %r",
                          entry_point, filename)
    if found_errors:
        raise RuntimeError("Errors found while loading scripts."
                           " See log file for details")
    return entry_points

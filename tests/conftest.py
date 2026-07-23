"""Shared test configuration.

MathCAT and liblouis are optional native engines that may or may not be
installed on a given machine (CI has neither; a developer box might have
both). To keep the suite deterministic and identical everywhere, their
auto-detection is disabled for the whole run: the app-level tests exercise
our own tables, while test_mathcat.py and test_liblouis.py drive the
adapters with injected fake libraries, which bypass these switches.
"""

import os

os.environ["DISVIMAT_NO_MATHCAT"] = "1"
os.environ["DISVIMAT_NO_LIBLOUIS"] = "1"
# Likewise for add-ons: tests must not depend on what is installed or on a
# DISVIMAT_ADDONS folder the developer happens to have set.
os.environ["DISVIMAT_NO_ADDONS"] = "1"
# And the personal keymap: point it at a file that does not exist so a real
# ~/.disvimat/user_keys.json on the developer's box cannot alter results.
# Tests that exercise reassignment pass their own path explicitly.
os.environ["DISVIMAT_USER_KEYMAP"] = os.path.join(
    os.path.dirname(__file__), "no_such_user_keys.json"
)

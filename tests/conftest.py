"""Shared test configuration.

MathCAT is a process-global singleton and may or may not be installed on a
given machine (CI has none, a developer box might). To keep the suite
deterministic and identical everywhere, speech and braille auto-detection
is disabled for the whole run: the app-level tests exercise our own
tables, and ``test_mathcat.py`` drives the adapter with an injected fake
library, which bypasses this switch.
"""

import os

os.environ["DISVIMAT_NO_MATHCAT"] = "1"

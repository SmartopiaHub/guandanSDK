"""Convenience namespace for the Python Guandan package.

The canonical core API lives in :mod:`guandan_core`, mirroring the Dart package
name. This namespace exists so the Python distribution can also be imported as
``py_guandan`` when desired.
"""

from guandan_core import *  # noqa: F401,F403

"""Settings lookup for Social Auth on Flask.

Settings live in ``current_app.config``, falling back to the process
environment so that the storage layer keeps working outside an app context.
"""

from __future__ import annotations

import os
from typing import Any

from flask import current_app

_MISSING = object()


def get_setting(name: str) -> Any:
    """Return the configured value for ``name`` or raise ``KeyError``."""
    try:
        config = current_app.config
    except RuntimeError:
        config = {}
    value = config.get(name, _MISSING)
    if value is _MISSING:
        value = os.environ.get(name, _MISSING)
    if value is _MISSING:
        raise KeyError(name)
    return value


def get_setting_default(name: str, default: Any = None) -> Any:
    """Return the configured value for ``name`` or ``default``."""
    try:
        return get_setting(name)
    except KeyError:
        return default

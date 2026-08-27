from urllib.parse import quote

from flask import current_app, request
from social_core.backends.utils import user_backends_data

from .utils import REDIRECT_FIELD_NAME, Storage
from .views import get_current_user


class LazyDict:
    """Lazy dict initialization."""

    def __init__(self, factory) -> None:
        self._factory = factory
        self._wrapped = None

    def _setup(self):
        if self._wrapped is None:
            self._wrapped = self._factory()
        return self._wrapped

    def __getitem__(self, name):
        return self._setup()[name]

    def __setitem__(self, name, value) -> None:
        self._setup()[name] = value

    def __iter__(self):
        return iter(self._setup())


def backends():
    """
    Load Social Auth current user data to context under the key 'backends'.
    Will return the output of social_core.backends.utils.user_backends_data.
    """
    return {
        "backends": LazyDict(
            lambda: user_backends_data(
                get_current_user(),
                current_app.config.get("AUTHENTICATION_BACKENDS", []),
                Storage,
            )
        )
    }


def login_redirect():
    """Load current redirect to context."""
    try:
        value = (request.method == "POST" and request.form.get(REDIRECT_FIELD_NAME)) or request.args.get(
            REDIRECT_FIELD_NAME
        )
    except ValueError:
        # request form data may be malformed
        value = None
    if value:
        value = quote(value)
        querystring = REDIRECT_FIELD_NAME + "=" + value
    else:
        querystring = ""

    return {
        "REDIRECT_FIELD_NAME": REDIRECT_FIELD_NAME,
        "REDIRECT_FIELD_VALUE": value,
        "REDIRECT_QUERYSTRING": querystring,
    }

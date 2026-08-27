"""Translate Social Auth exceptions into a user message plus a redirect.

The Django binding ships this as a middleware with a ``process_exception``
hook; Flask has no such hook, so the equivalent is an error handler registered
for ``SocialAuthBaseException``.
"""

from __future__ import annotations

from urllib.parse import quote

from flask import current_app, flash, g
from flask import redirect as flask_redirect
from social_core.exceptions import SocialAuthBaseException
from social_core.utils import social_logger


def raise_exception(strategy, backend) -> bool:
    return bool(strategy.setting("RAISE_EXCEPTIONS", current_app.debug, backend=backend))


def get_message(exception) -> str:
    return str(exception)


def get_redirect_uri(strategy, backend) -> str | None:
    return strategy.setting("LOGIN_ERROR_URL", backend=backend)


def social_auth_exception_handler(exception):
    """
    Provide the user with a message, log an error, and redirect to some next
    location.

    By default, the exception message itself is sent to the user and they are
    redirected to the location specified in the SOCIAL_AUTH_LOGIN_ERROR_URL
    setting.
    """
    strategy = getattr(g, "social_strategy", None)
    backend = getattr(g, "backend", None)
    if strategy is None or raise_exception(strategy, backend):
        raise exception

    backend_name = getattr(backend, "name", "unknown-backend")
    message = get_message(exception)
    url = get_redirect_uri(strategy, backend)

    social_logger.info(message)
    try:
        flash(message, f"social-auth {backend_name}")
    except RuntimeError:
        # The message framework is unavailable (no session on this request)
        if url:
            url += (("?" in url and "&") or "?") + f"message={quote(message)}&backend={backend_name}"

    if url:
        return flask_redirect(url)
    raise exception


def register_exception_handler(app) -> None:
    app.register_error_handler(SocialAuthBaseException, social_auth_exception_handler)

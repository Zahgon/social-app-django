from functools import wraps

from flask import abort, g, has_request_context, url_for
from flask import request as flask_request
from social_core.exceptions import MissingBackend
from social_core.utils import get_strategy, module_member, setting_name

from .settings import get_setting_default

STRATEGY = get_setting_default(setting_name("STRATEGY"), "social_flask.strategy.FlaskStrategy")
STORAGE = get_setting_default(setting_name("STORAGE"), "social_flask.models.FlaskStorage")

Strategy = module_member(STRATEGY)
Storage = module_member(STORAGE)

REDIRECT_FIELD_NAME = "next"


def load_strategy(request=None):
    if request is None and has_request_context():
        request = flask_request
    return get_strategy(STRATEGY, STORAGE, request)


def load_backend(strategy, name, redirect_uri):
    return strategy.get_backend(name, redirect_uri=redirect_uri)


def psa(redirect_uri=None, load_strategy=load_strategy):
    def decorator(func):
        @wraps(func)
        def wrapper(backend, *args, **kwargs):
            uri = redirect_uri
            if uri and not uri.startswith("/"):
                uri = url_for(redirect_uri, backend=backend)
            g.social_strategy = load_strategy()
            # backward compatibility in attribute name, only if not already
            # defined
            if not hasattr(g, "strategy"):
                g.strategy = g.social_strategy

            try:
                g.backend = load_backend(g.social_strategy, backend, redirect_uri=uri)
            except MissingBackend:
                abort(404, "Backend not found")
            return func(backend, *args, **kwargs)

        return wrapper

    return decorator

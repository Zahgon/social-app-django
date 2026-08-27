from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

from flask import Response
from flask import redirect as flask_redirect
from flask import render_template, render_template_string
from flask import session as flask_session
from social_core.strategy import BaseStrategy, BaseTemplateStrategy
from social_core.utils import (
    PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME,
    module_member,
)
from werkzeug.datastructures import MultiDict

from .db import Base, session as db_session
from .settings import get_setting, get_setting_default

if TYPE_CHECKING:
    from social_core.backends.base import BaseAuth
    from social_core.storage import PartialMixin


PARTIAL_PIPELINE_CONFIRMATION_NONCE_PARAMETER = "partial_pipeline_confirm_nonce"

RESUME_CONFIRMATION_TEMPLATE = "social_flask/partial_pipeline_external_resume.html"


class FlaskTemplateStrategy(BaseTemplateStrategy):
    def render_template(self, tpl, context):
        return render_template(tpl, **(context or {}))

    def render_string(self, html, context):
        return render_template_string(html, **(context or {}))


class FlaskStrategy(BaseStrategy):
    DEFAULT_TEMPLATE_STRATEGY = FlaskTemplateStrategy

    def __init__(self, storage, request=None, tpl=None) -> None:
        self.request = request
        self._session: dict[str, Any] | None = None
        super().__init__(storage, tpl)

    @property
    def session(self):
        """The Flask session when a request is being served, a plain dict
        otherwise (``social-core`` uses the strategy outside requests too)."""
        if self.request is not None:
            return flask_session
        if self._session is None:
            self._session = {}
        return self._session

    def get_setting(self, name):
        value = get_setting(name)
        # Force text on URL named settings that are lazily evaluated
        if name.endswith("_URL") and not isinstance(value, str):
            value = str(value)
        return value

    def request_data(self, merge=True):
        if not self.request:
            return {}
        if merge:
            data = MultiDict(self.request.args)
            data.update(self.request.form)
        elif self.request.method == "POST":
            data = MultiDict(self.request.form)
        else:
            data = MultiDict(self.request.args)
        return data

    def request_host(self):
        if self.request:
            return self.request.host
        return None

    def request_is_secure(self):
        """Is the request using HTTPS?"""
        return self.request.is_secure

    def request_path(self):
        """Path of the current request"""
        return self.request.path

    def request_port(self):
        """Port in use for this request"""
        return self.request.environ["SERVER_PORT"]

    def request_get(self):
        """Request GET data"""
        return MultiDict(self.request.args)

    def request_post(self):
        """Request POST data"""
        return MultiDict(self.request.form)

    def redirect(self, url):
        return flask_redirect(url)

    def html(self, content):
        return Response(content, mimetype="text/html")

    def partial_pipeline_external_resume_confirmation(
        self,
        backend: BaseAuth,
        partial: PartialMixin,
        request_data: dict[str, Any],
    ) -> Response | None:
        if not self.request:
            return None

        nonce = self.random_string(32)
        self.session_set(PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME, nonce)
        confirmation_parameter = backend.setting(
            "PARTIAL_PIPELINE_EXTERNAL_RESUME_CONFIRMATION_PARAMETER",
            "partial_pipeline_confirm",
        )
        return self.html(
            render_template(
                RESUME_CONFIRMATION_TEMPLATE,
                action_url=self.request.path,
                backend=backend,
                backend_name=backend.name,
                confirmation_parameter=confirmation_parameter,
                confirmation_value="1",
                confirmation_nonce_parameter=PARTIAL_PIPELINE_CONFIRMATION_NONCE_PARAMETER,
                confirmation_nonce=nonce,
                partial=partial,
            )
        )

    def partial_pipeline_external_resume_confirmed(
        self,
        backend: BaseAuth,
        request_data: dict[str, Any],
    ) -> bool:
        if not self.request or self.request.method != "POST":
            return False

        confirmation_parameter = backend.setting(
            "PARTIAL_PIPELINE_EXTERNAL_RESUME_CONFIRMATION_PARAMETER",
            "partial_pipeline_confirm",
        )
        if not confirmation_parameter or confirmation_parameter not in request_data:
            return False

        expected_nonce = self.session_get(PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME)
        submitted_nonce = request_data.get(PARTIAL_PIPELINE_CONFIRMATION_NONCE_PARAMETER)
        return bool(expected_nonce) and submitted_nonce == expected_nonce

    def render_html(self, tpl=None, html=None, context=None):
        if not tpl and not html:
            msg = "Missing template or html parameters"
            raise ValueError(msg)
        context = context or {}
        if tpl:
            return render_template(tpl, **context)
        return render_template_string(html, **context)

    def authenticate(self, backend, *args, **kwargs):
        kwargs["strategy"] = self
        kwargs["storage"] = self.storage
        kwargs["backend"] = backend
        # pipelines don't want a positional request argument, but the backend
        # hands it back to clean_authenticate_args() positionally
        request = kwargs.pop("request", self.request)
        user = backend.authenticate(request, *args, **kwargs)
        if user is not None:
            # Record the backend that authenticated the user, the same way
            # django.contrib.auth.authenticate() does for the Django binding.
            user.backend = f"{type(backend).__module__}.{type(backend).__name__}"
        return user

    def clean_authenticate_args(self, request=None, *args, **kwargs):
        # pipelines don't want a positional request argument
        kwargs["request"] = request
        return args, kwargs

    def session_get(self, name, default=None):
        return self.session.get(name, default)

    def session_set(self, name, value) -> None:
        self.session[name] = value
        if hasattr(self.session, "modified"):
            self.session.modified = True

    def session_pop(self, name):
        return self.session.pop(name, None)

    def session_setdefault(self, name, value):
        return self.session.setdefault(name, value)

    def build_absolute_uri(self, path=None):
        if self.request:
            return urljoin(self.request.host_url, path) if path else self.request.url_root
        return path

    def to_session_value(self, val):
        """
        Converts values that are instance of a model to a dictionary with
        enough information to retrieve the instance back later.
        """
        if isinstance(val, MultiDict):
            val = val.to_dict()
        elif isinstance(val, Base):
            val = {"pk": val.id, "ctype": f"{type(val).__module__}.{type(val).__qualname__}"}
        return val

    def from_session_value(self, val):
        """Converts back the instance saved by to_session_value."""
        if isinstance(val, dict) and "pk" in val and "ctype" in val:
            model_class = module_member(val["ctype"])
            val = db_session.get(model_class, val["pk"])

        return val

    def get_language(self):
        """Return current language"""
        return get_setting_default("LANGUAGE_CODE", "en-us")

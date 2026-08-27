from unittest import mock

import pytest
from flask import Response
from flask import request as flask_request
from social_core.utils import PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME
from werkzeug.datastructures import MultiDict

from social_flask.models import User
from social_flask.strategy import PARTIAL_PIPELINE_CONFIRMATION_NONCE_PARAMETER
from social_flask.utils import load_backend, load_strategy


class LazyURL:
    """A lazily evaluated URL setting, the Flask stand-in for Django's
    ``gettext_lazy`` URL settings."""

    def __init__(self, value: str) -> None:
        self._value = value

    def __str__(self) -> str:
        return self._value


@pytest.fixture
def make_strategy(app):
    """Push a request context and return a strategy bound to that request."""
    contexts = []

    def _make(path="/", **kwargs):
        ctx = app.test_request_context(path, **kwargs)
        ctx.push()
        contexts.append(ctx)
        return load_strategy(request=flask_request._get_current_object())  # noqa: SLF001

    yield _make

    for ctx in reversed(contexts):
        ctx.pop()


@pytest.fixture
def strategy(make_strategy):
    return make_strategy("/", query_string={"x": "1"})


class TestStrategy:
    def test_request_methods(self, strategy, make_strategy):
        assert strategy.request_port() == "80"
        assert strategy.request_path() == "/"
        assert strategy.request_host() == "testserver"
        assert strategy.request_is_secure() is False
        assert strategy.request_data() == MultiDict([("x", "1")])
        assert strategy.request_get() == MultiDict([("x", "1")])
        assert strategy.request_post() == {}
        post_strategy = make_strategy("/", method="POST")
        assert post_strategy.request_data(merge=False) == {}

    def test_build_absolute_uri(self, strategy):
        assert strategy.build_absolute_uri("/") == "http://testserver/"

    def test_settings(self, app, strategy):
        app.config["LOGIN_ERROR_URL"] = "/"
        assert strategy.get_setting("LOGIN_ERROR_URL") == "/"
        app.config["LOGIN_ERROR_URL"] = LazyURL("/")
        assert strategy.get_setting("LOGIN_ERROR_URL") == "/"

    def test_session_methods(self, strategy):
        strategy.session_set("k", "v")
        assert strategy.session_get("k") == "v"
        assert strategy.session_setdefault("k", "x") == "v"
        assert strategy.session_pop("k") == "v"

    def test_random_string(self, strategy):
        rs1 = strategy.random_string()
        assert len(rs1) == 12
        assert rs1 != strategy.random_string()

    def test_session_value(self, strategy):
        user = User.create_user(username="test")

        val = strategy.to_session_value(val=user)
        assert val == {"pk": user.id, "ctype": "social_flask.models.User"}

        instance = strategy.from_session_value(val=val)
        assert instance == user

    def test_session_value_flattens_request_data(self, make_strategy):
        strategy = make_strategy(
            "/complete/facebook/",
            query_string={"partial_token": "external-token", "verification_code": "code"},
        )

        val = strategy.to_session_value(strategy.request_data())

        assert val == {"partial_token": "external-token", "verification_code": "code"}

    def test_get_language(self, strategy):
        assert strategy.get_language() == "en-us"

    def test_html(self, strategy):
        result = strategy.render_html(tpl="test.html")
        assert result == "test\n"

        result = strategy.render_html(html="xoxo")
        assert result == "xoxo"

        with pytest.raises(ValueError, match="Missing template or html parameters"):
            strategy.render_html()

        result = strategy.html(content="xoxo")
        assert isinstance(result, Response)
        assert result.data == b"xoxo"

        ctx = {"x": 1}
        result = strategy.tpl.render_template(tpl="test.html", context=ctx)
        assert result == "test\n"

        result = strategy.tpl.render_string(html="xoxo", context=ctx)
        assert result == "xoxo"

    def test_partial_pipeline_external_resume_confirmation(self, make_strategy):
        strategy = make_strategy(
            "/complete/facebook/",
            query_string={"partial_token": "external-token", "verification_code": "code"},
        )
        backend = load_backend(strategy=strategy, name="facebook", redirect_uri="/")

        response = strategy.partial_pipeline_external_resume_confirmation(backend, mock.Mock(), strategy.request_data())

        assert isinstance(response, Response)
        nonce = strategy.session_get(PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME)
        assert nonce
        content = response.data.decode()
        assert 'action="/complete/facebook/"' in content
        assert 'name="partial_pipeline_confirm"' in content
        assert f'name="{PARTIAL_PIPELINE_CONFIRMATION_NONCE_PARAMETER}"' in content
        assert f'value="{nonce}"' in content
        assert "partial_token" not in content
        assert "verification_code" not in content

    def test_partial_pipeline_external_resume_confirmation_uses_custom_parameter(self, app, make_strategy):
        strategy = make_strategy("/complete/facebook/")
        backend = load_backend(strategy=strategy, name="facebook", redirect_uri="/")

        app.config["SOCIAL_AUTH_PARTIAL_PIPELINE_EXTERNAL_RESUME_CONFIRMATION_PARAMETER"] = "continue_auth"
        response = strategy.partial_pipeline_external_resume_confirmation(backend, mock.Mock(), strategy.request_data())

        content = response.data.decode()
        assert 'name="continue_auth"' in content
        assert 'name="partial_pipeline_confirm"' not in content
        assert f'name="{PARTIAL_PIPELINE_CONFIRMATION_NONCE_PARAMETER}"' in content

    def test_partial_pipeline_external_resume_confirmed(self, make_strategy):
        strategy = make_strategy(
            "/complete/facebook/",
            method="POST",
            data={
                "partial_pipeline_confirm": "1",
                PARTIAL_PIPELINE_CONFIRMATION_NONCE_PARAMETER: "nonce",
            },
        )
        backend = load_backend(strategy=strategy, name="facebook", redirect_uri="/")
        strategy.session_set(PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME, "nonce")

        assert strategy.partial_pipeline_external_resume_confirmed(backend, strategy.request_data()) is True

    def test_partial_pipeline_external_resume_confirmed_uses_custom_parameter(self, app, make_strategy):
        strategy = make_strategy(
            "/complete/facebook/",
            method="POST",
            data={
                "continue_auth": "1",
                PARTIAL_PIPELINE_CONFIRMATION_NONCE_PARAMETER: "nonce",
            },
        )
        backend = load_backend(strategy=strategy, name="facebook", redirect_uri="/")
        strategy.session_set(PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME, "nonce")

        app.config["SOCIAL_AUTH_PARTIAL_PIPELINE_EXTERNAL_RESUME_CONFIRMATION_PARAMETER"] = "continue_auth"
        assert strategy.partial_pipeline_external_resume_confirmed(backend, strategy.request_data()) is True

    def test_partial_pipeline_external_resume_confirmation_without_request(self, app):
        strategy = load_strategy()
        backend = load_backend(strategy=strategy, name="facebook", redirect_uri="/")

        assert strategy.partial_pipeline_external_resume_confirmation(backend, mock.Mock(), {}) is None

    def test_partial_pipeline_external_resume_confirmed_without_request(self, app):
        strategy = load_strategy()
        backend = load_backend(strategy=strategy, name="facebook", redirect_uri="/")
        strategy.session_set(PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME, "nonce")

        assert (
            strategy.partial_pipeline_external_resume_confirmed(
                backend,
                {
                    "partial_pipeline_confirm": "1",
                    PARTIAL_PIPELINE_CONFIRMATION_NONCE_PARAMETER: "nonce",
                },
            )
            is False
        )

    def test_partial_pipeline_external_resume_confirmation_rejects_get(self, strategy):
        backend = load_backend(strategy=strategy, name="facebook", redirect_uri="/")
        strategy.session_set(PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME, "nonce")

        assert strategy.partial_pipeline_external_resume_confirmed(backend, strategy.request_data()) is False

    def test_partial_pipeline_external_resume_confirmation_rejects_missing_parameter(self, make_strategy):
        strategy = make_strategy(
            "/complete/facebook/",
            method="POST",
            data={PARTIAL_PIPELINE_CONFIRMATION_NONCE_PARAMETER: "nonce"},
        )
        backend = load_backend(strategy=strategy, name="facebook", redirect_uri="/")
        strategy.session_set(PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME, "nonce")

        assert strategy.partial_pipeline_external_resume_confirmed(backend, strategy.request_data()) is False

    def test_partial_pipeline_external_resume_confirmation_rejects_missing_nonce(self, make_strategy):
        strategy = make_strategy(
            "/complete/facebook/",
            method="POST",
            data={"partial_pipeline_confirm": "1"},
        )
        backend = load_backend(strategy=strategy, name="facebook", redirect_uri="/")
        strategy.session_set(PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME, "nonce")

        assert strategy.partial_pipeline_external_resume_confirmed(backend, strategy.request_data()) is False

    def test_partial_pipeline_external_resume_confirmation_rejects_wrong_nonce(self, make_strategy):
        strategy = make_strategy(
            "/complete/facebook/",
            method="POST",
            data={
                "partial_pipeline_confirm": "1",
                PARTIAL_PIPELINE_CONFIRMATION_NONCE_PARAMETER: "wrong",
            },
        )
        backend = load_backend(strategy=strategy, name="facebook", redirect_uri="/")
        strategy.session_set(PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME, "nonce")

        assert strategy.partial_pipeline_external_resume_confirmed(backend, strategy.request_data()) is False

    def test_authenticate(self, strategy):
        backend = load_backend(strategy=strategy, name="facebook", redirect_uri="/")
        user = mock.Mock()
        with mock.patch("social_core.backends.base.BaseAuth.pipeline", return_value=user):
            result = strategy.authenticate(backend=backend, response=mock.Mock())
            assert result == user
            assert result.backend == "social_core.backends.facebook.FacebookOAuth2"

    def test_clean_authenticate_args(self, strategy):
        request = flask_request._get_current_object()  # noqa: SLF001
        args, kwargs = strategy.clean_authenticate_args(request)
        assert args == ()
        assert kwargs == {"request": request}

    def test_clean_authenticate_args_none(self, strategy):
        # When called from continue_pipeline(), request is None. Issue #222
        args, kwargs = strategy.clean_authenticate_args(None)
        assert args == ()
        assert kwargs == {"request": None}

    def test_session_creation_without_request(self, app):
        strategy = load_strategy()
        assert strategy.request is None
        assert strategy.session is not None

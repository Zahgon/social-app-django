import logging
from unittest import mock

import pytest
from flask import url_for
from social_core.exceptions import AuthCanceled


class MockAuthCanceled(AuthCanceled):
    def __init__(self, *args, **kwargs) -> None:
        if not args:
            kwargs.setdefault("backend", None)
        super().__init__(*args, **kwargs)


@pytest.fixture(autouse=True)
def _mocked_backend_request():
    with mock.patch("social_core.backends.base.BaseAuth.request", side_effect=MockAuthCanceled):
        yield


@pytest.fixture
def complete_url(app):
    return url_for("social.complete", backend="facebook") + "?code=2&state=1"


@pytest.fixture
def client(app):
    app.config.update(SOCIAL_AUTH_FACEBOOK_KEY="1", SOCIAL_AUTH_FACEBOOK_SECRET="2")  # noqa: S106
    client = app.test_client()
    with client.session_transaction() as session:
        session["facebook_state"] = "1"
    return client


class TestMiddleware:
    def test_exception(self, client, complete_url):
        with pytest.raises(MockAuthCanceled):
            client.get(complete_url)

    def test_exception_debug(self, app, client, complete_url):
        app.debug = True
        logging.disable(logging.CRITICAL)
        with pytest.raises(MockAuthCanceled):
            client.get(complete_url)
        logging.disable(logging.NOTSET)

    def test_login_error_url(self, app, client, complete_url):
        app.config["SOCIAL_AUTH_LOGIN_ERROR_URL"] = "/"
        response = client.get(complete_url)
        assert response.status_code == 302
        assert response.location == "/"

    def test_message_failure(self, app, client, complete_url):
        app.config["SOCIAL_AUTH_LOGIN_ERROR_URL"] = "/"
        with mock.patch("social_flask.middleware.flash", side_effect=RuntimeError):
            response = client.get(complete_url)
        assert response.status_code == 302
        assert response.location == "/?message=Authentication%20process%20canceled&backend=facebook"

    def test_backend_specific_login_error_url(self, app, client, complete_url):
        app.config.update(
            SOCIAL_AUTH_LOGIN_ERROR_URL="/default-error",
            SOCIAL_AUTH_FACEBOOK_LOGIN_ERROR_URL="/facebook-error",
        )
        response = client.get(complete_url)
        assert response.status_code == 302
        assert response.location == "/facebook-error"

    def test_backend_specific_raise_exceptions(self, app, client, complete_url):
        app.debug = False
        app.config.update(
            SOCIAL_AUTH_RAISE_EXCEPTIONS=False,
            SOCIAL_AUTH_FACEBOOK_RAISE_EXCEPTIONS=True,
        )
        logging.disable(logging.CRITICAL)
        with pytest.raises(MockAuthCanceled):
            client.get(complete_url)
        logging.disable(logging.NOTSET)

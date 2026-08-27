from unittest import mock

import pytest
from flask import url_for

from social_flask.models import User, UserSocialAuth
from social_flask.views import get_session_timeout


@pytest.fixture
def facebook_app(app):
    app.config.update(SOCIAL_AUTH_FACEBOOK_KEY="1", SOCIAL_AUTH_FACEBOOK_SECRET="2")  # noqa: S106
    return app


@pytest.fixture
def facebook_client(facebook_app):
    client = facebook_app.test_client()
    with client.session_transaction() as session:
        session["facebook_state"] = "1"
    return client


class TestViews:
    def test_begin_view(self, facebook_client):
        response = facebook_client.post(url_for("social.begin", backend="facebook"))
        assert response.status_code == 302

        url = url_for("social.begin", backend="blabla")
        response = facebook_client.post(url)
        assert response.status_code == 404

    def test_begin_view_requires_post(self, facebook_client):
        response = facebook_client.get(url_for("social.begin", backend="facebook"))
        assert response.status_code == 405

    @mock.patch("social_core.backends.base.BaseAuth.request")
    def test_complete(self, mock_request, facebook_client):
        url = url_for("social.complete", backend="facebook")
        url += "?code=2&state=1"
        mock_request.return_value.json.return_value = {"access_token": "123"}
        with mock.patch(
            "social_flask.views.set_session_expiry",
            side_effect=[OverflowError, None],
        ):
            response = facebook_client.get(url)
            assert response.status_code == 302
            assert response.location == "/accounts/profile/"

    @mock.patch("social_core.backends.base.BaseAuth.request")
    def test_disconnect(self, _mock_request, facebook_client):
        user = User.create_user(username="test", password="pwd")  # noqa: S106
        UserSocialAuth(user=user, provider="facebook", uid="some-mock-facebook-uid").save()
        with facebook_client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        url = url_for("social.disconnect", backend="facebook")
        response = facebook_client.post(url)
        assert response.status_code == 302
        assert response.location == "http://testserver/accounts/profile/"

        url = url_for("social.disconnect_individual", backend="facebook", association_id=123)
        hup = User.has_usable_password
        del User.has_usable_password
        try:
            response = facebook_client.post(url)
            assert response.status_code == 302
            assert response.location == "http://testserver/accounts/profile/"
        finally:
            User.has_usable_password = hup


class TestGetSessionTimeout:
    """
    Ensure that the branching logic of get_session_timeout behaves as expected.
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.social_user = mock.MagicMock()
        self.social_user.expiration_datetime.return_value = None

    def set_user_expiration(self, seconds):
        self.social_user.expiration_datetime.return_value = mock.MagicMock(
            total_seconds=mock.MagicMock(return_value=seconds),
        )

    def test_expiration_disabled_no_max(self):
        self.set_user_expiration(60)
        expiration_length = get_session_timeout(self.social_user, enable_session_expiration=False)
        assert expiration_length is None

    def test_expiration_disabled_with_max(self):
        expiration_length = get_session_timeout(
            self.social_user,
            enable_session_expiration=False,
            max_session_length=60,
        )
        assert expiration_length == 60

    def test_expiration_disabled_with_zero_max(self):
        expiration_length = get_session_timeout(
            self.social_user, enable_session_expiration=False, max_session_length=0
        )
        assert expiration_length == 0

    def test_user_has_session_length_no_max(self):
        self.set_user_expiration(60)
        expiration_length = get_session_timeout(self.social_user, enable_session_expiration=True)
        assert expiration_length == 60

    def test_user_has_session_length_larger_max(self):
        self.set_user_expiration(60)
        expiration_length = get_session_timeout(
            self.social_user, enable_session_expiration=True, max_session_length=90
        )
        assert expiration_length == 60

    def test_user_has_session_length_smaller_max(self):
        self.set_user_expiration(60)
        expiration_length = get_session_timeout(
            self.social_user, enable_session_expiration=True, max_session_length=30
        )
        assert expiration_length == 30

    def test_user_has_no_session_length_with_max(self):
        expiration_length = get_session_timeout(
            self.social_user, enable_session_expiration=True, max_session_length=60
        )
        assert expiration_length == 60

    def test_user_has_no_session_length_no_max(self):
        expiration_length = get_session_timeout(self.social_user, enable_session_expiration=True)
        assert expiration_length is None

from datetime import timedelta
from unittest import mock

import pytest
from social_core.exceptions import AuthAlreadyAssociated
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from social_flask.clearsocial import clearsocial
from social_flask.db import session as db_session
from social_flask.models import (
    AbstractUserSocialAuth,
    Association,
    Code,
    FlaskStorage,
    Nonce,
    Partial,
    User,
    UserSocialAuth,
)


def count(model) -> int:
    return db_session.query(model).count()


def make_integrity_error() -> IntegrityError:
    return IntegrityError("INSERT", (), Exception("duplicate"))


@pytest.mark.usefixtures("app")
class TestSocialAuthUser:
    def test_user_relationship_none(self):
        """Accessing User.social_user outside of the pipeline doesn't work"""
        user = User.create_user(username="randomtester")
        with pytest.raises(AttributeError):
            user.social_user  # noqa: B018

    def test_user_existing_relationship(self):
        """Accessing User.social_user outside of the pipeline doesn't work"""
        user = User.create_user(username="randomtester")
        UserSocialAuth(user=user, provider="my-provider", uid="1234").save()
        with pytest.raises(AttributeError):
            user.social_user  # noqa: B018

    def test_get_social_auth(self):
        user = User.create_user(username="randomtester")
        user_social = UserSocialAuth(user=user, provider="my-provider", uid="1234").save()
        other = UserSocialAuth.get_social_auth("my-provider", "1234")
        assert other == user_social

    def test_get_social_auth_none(self):
        other = UserSocialAuth.get_social_auth("my-provider", "1234")
        assert other is None

    def test_cleanup(self):
        Code(email="first@example.com").save()
        Code(email="second@example.com").save()
        code = Code(email="expire@example.com").save()
        code.timestamp -= timedelta(days=30)
        code.save()

        Partial().save()
        partial = Partial().save()
        partial.timestamp -= timedelta(days=30)
        partial.save()

        clearsocial()

        assert count(Code) == 2
        assert count(Partial) == 1


class TestUserSocialAuth:
    @pytest.fixture(autouse=True)
    def _setup(self, app):
        self.app = app
        self.user_model = User
        self.user = User.create_user(username="randomtester", email="user@example.com")
        self.usa = UserSocialAuth(user=self.user, provider="my-provider", uid="1234").save()

    def test_changed(self):
        self.user.email = eml = "test@example.com"
        UserSocialAuth.changed(user=self.user)
        db_eml = db_session.scalars(select(self.user_model).filter_by(username=self.user.username)).one().email
        assert db_eml == eml

    def test_set_extra_data(self):
        self.usa.set_extra_data({"a": "b"})
        db_session.expire(self.usa)
        db_data = db_session.get(UserSocialAuth, self.usa.id).extra_data
        assert db_data == {"a": "b"}

    def test_disconnect(self):
        m = mock.Mock()
        UserSocialAuth.disconnect(m)
        assert m.method_calls == [mock.call.delete()]

    def test_username_field(self):
        assert UserSocialAuth.username_field() == "username"
        with mock.patch(
            "social_flask.models.UserSocialAuth.user_model",
            return_value=mock.Mock(USERNAME_FIELD="test"),
        ):
            assert UserSocialAuth.username_field() == "test"

    def test_user_exists(self):
        assert UserSocialAuth.user_exists(username=self.user.username) is True
        assert UserSocialAuth.user_exists(username="test") is False

    def test_get_username(self):
        assert UserSocialAuth.get_username(self.user) == self.user.username

    def test_create_user(self):
        UserSocialAuth.create_user(username="testuser")

    def test_create_user_reraise(self):
        with pytest.raises(AuthAlreadyAssociated):
            UserSocialAuth.create_user(username=self.user.username, email=None)

    @mock.patch("social_flask.models.UserSocialAuth.username_field", return_value="email")
    @mock.patch("social_flask.models.User.create_user", return_value="<User>")
    def test_create_user_custom_username(self, *args):
        UserSocialAuth.create_user(username=self.user.email)

    @mock.patch("social_flask.models.User.create_user", side_effect=make_integrity_error())
    def test_create_user_existing(self, *args):
        with pytest.raises(AuthAlreadyAssociated):
            UserSocialAuth.create_user(username=self.user.email)

    def test_get_user(self):
        assert UserSocialAuth.get_user(pk=self.user.id) == self.user
        assert UserSocialAuth.get_user(pk=123) is None

    def test_get_users_by_email(self):
        qs = UserSocialAuth.get_users_by_email(email=self.user.email)
        assert qs.count() == 1
        self.user.is_active = False
        self.user.save()
        qs = UserSocialAuth.get_users_by_email(email=self.user.email)
        assert qs.count() == 0
        self.app.config["SOCIAL_AUTH_ACTIVE_USERS_FILTER"] = {}
        try:
            qs = UserSocialAuth.get_users_by_email(email=self.user.email)
            assert qs.count() == 1
        finally:
            del self.app.config["SOCIAL_AUTH_ACTIVE_USERS_FILTER"]

    def test_get_social_auth(self):
        usa = self.usa
        # Model
        assert UserSocialAuth.get_social_auth(provider=usa.provider, uid=usa.uid) == usa
        assert UserSocialAuth.get_social_auth(provider="a", uid="1") is None

        # Mixin
        assert super(AbstractUserSocialAuth, usa).get_social_auth(provider=usa.provider, uid=usa.uid) == usa
        assert super(AbstractUserSocialAuth, usa).get_social_auth(provider="a", uid="1") is None

    def test_get_social_auth_int_uid(self):
        usa = self.usa
        int_uid = int(usa.uid)

        # Model
        assert UserSocialAuth.get_social_auth(provider=usa.provider, uid=int_uid) == usa

        # Mixin
        assert super(AbstractUserSocialAuth, usa).get_social_auth(provider=usa.provider, uid=usa.uid) == usa

        # Storage entry point
        assert FlaskStorage.user.get_social_auth(provider=usa.provider, uid=int_uid) == usa

    def test_get_social_auth_for_user(self):
        qs = UserSocialAuth.get_social_auth_for_user(user=self.user, provider=self.usa.provider, id=self.usa.id)
        assert qs.count() == 1

    def test_create_social_auth(self):
        usa = UserSocialAuth.create_social_auth(user=self.user, provider="test", uid=1)
        assert usa.uid == "1"
        assert str(usa) == str(self.user)

    def test_username_max_length(self):
        assert UserSocialAuth.username_max_length() == 150


@pytest.mark.usefixtures("app")
class TestNonce:
    def test_use(self):
        assert count(Nonce) == 0
        assert Nonce.use(server_url="/", timestamp=1, salt="1") is True
        assert Nonce.use(server_url="/", timestamp=1, salt="1") is False
        assert count(Nonce) == 1


@pytest.mark.usefixtures("app")
class TestAssociation:
    def test_store_get_remove(self):
        Association.store(
            server_url="/",
            association=mock.Mock(handle="a", secret=b"b", issued=1, lifetime=2, assoc_type="c"),
        )

        qs = Association.get(handle="a")
        assert qs.count() == 1
        assert qs[0].secret == "Yg==\n"

        Association.remove(ids_to_delete=[qs.first().id])
        assert count(Association) == 0


@pytest.mark.usefixtures("app")
class TestCode:
    def test_get_code(self):
        code1 = Code(email="test@example.com", code="abc").save()
        code2 = Code.get_code(code="abc")
        assert code1 == code2
        assert Code.get_code(code="xyz") is None


@pytest.mark.usefixtures("app")
class TestPartial:
    def test_load_destroy(self):
        token_value = "x"  # noqa: S105
        p = Partial(token=token_value, backend="y", data={}).save()
        assert Partial.load(token=token_value) == p
        assert Partial.load(token="y") is None  # noqa: S106

        Partial.destroy(token=token_value)
        assert count(Partial) == 0


class TestFlaskStorage:
    def test_is_integrity_error(self):
        assert FlaskStorage.is_integrity_error(make_integrity_error()) is True

"""SQLAlchemy storage mixins for Social Auth"""

from __future__ import annotations

import base64

from social_core.exceptions import AuthAlreadyAssociated
from social_core.storage import (
    AssociationMixin,
    BaseStorage,
    CodeMixin,
    NonceMixin,
    PartialMixin,
    UserMixin,
)
from social_core.utils import setting_name
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .db import QuerySet, session
from .settings import get_setting_default


class FlaskUserMixin(UserMixin):
    """Social Auth association model"""

    @classmethod
    def changed(cls, user):
        session.add(user)
        session.commit()

    def set_extra_data(self, extra_data=None):
        if super().set_extra_data(extra_data):
            self.save()

    @classmethod
    def allowed_to_disconnect(cls, user, backend_name, association_id=None):
        statement = select(cls).where(cls.user_id == user.id)
        if association_id is not None:
            statement = statement.where(cls.id != association_id)
        else:
            statement = statement.where(cls.provider != backend_name)

        valid_password = user.has_usable_password() if hasattr(user, "has_usable_password") else True
        return valid_password or QuerySet(statement).exists()

    @classmethod
    def disconnect(cls, entry):
        entry.delete()

    @classmethod
    def username_field(cls):
        return getattr(cls.user_model(), "USERNAME_FIELD", "username")

    @classmethod
    def user_exists(cls, *args, **kwargs) -> bool:
        """
        Return True/False if a User instance exists with the given arguments.
        Arguments are directly passed to filter_users().
        """
        if "username" in kwargs:
            kwargs[cls.username_field()] = kwargs.pop("username")
        return cls.filter_users(*args, **kwargs).exists()

    @classmethod
    def get_username(cls, user):
        return getattr(user, cls.username_field(), None)

    @classmethod
    def create_user(cls, *args, **kwargs):
        username_field = cls.username_field()
        user_model = cls.user_model()
        if "username" in kwargs:
            if username_field not in kwargs:
                kwargs[username_field] = kwargs.pop("username")
            elif "username" not in user_model.__table__.columns:
                # If username_field is 'email' and there is no field named
                # "username" then latest should be removed from kwargs.
                kwargs.pop("username")

        try:
            return user_model.create_user(*args, **kwargs)
        except IntegrityError as exc:
            session.rollback()
            raise AuthAlreadyAssociated(None) from exc

    @classmethod
    def filter_users(cls, *args, **kwargs) -> QuerySet:
        return QuerySet(select(cls.user_model()).filter_by(**kwargs))

    @classmethod
    def filter_active_users(cls, *args, **kwargs) -> QuerySet:
        kwargs.update(cls.active_users_filter())
        return cls.filter_users(*args, **kwargs)

    @classmethod
    def active_users_filter(cls) -> dict:
        return get_setting_default(setting_name("ACTIVE_USERS_FILTER"), {"is_active": True})

    @classmethod
    def get_user(cls, pk=None, **kwargs):
        if pk:
            kwargs = {"id": pk}
        users = cls.filter_active_users(**kwargs)
        if len(users) != 1:
            return None
        return users[0]

    @classmethod
    def get_users_by_email(cls, email) -> QuerySet:
        user_model = cls.user_model()
        email_field = getattr(user_model, "EMAIL_FIELD", "email")
        statement = (
            select(user_model).where(getattr(user_model, email_field).ilike(email)).filter_by(**cls.active_users_filter())
        )
        return QuerySet(statement)

    @classmethod
    def get_social_auth(cls, provider, uid):
        if not isinstance(uid, str):
            uid = str(uid)
        return session.scalars(select(cls).filter_by(provider=provider, uid=uid)).first()

    @classmethod
    def get_social_auth_for_user(cls, user, provider=None, id=None) -> QuerySet:  # noqa: A002
        statement = select(cls).where(cls.user_id == user.id)

        if provider:
            statement = statement.where(cls.provider == provider)

        if id:
            statement = statement.where(cls.id == id)
        return QuerySet(statement)

    @classmethod
    def create_social_auth(cls, user, uid, provider):
        if not isinstance(uid, str):
            uid = str(uid)
        return cls(user=user, uid=uid, provider=provider).save()


class FlaskNonceMixin(NonceMixin):
    @classmethod
    def use(cls, server_url, timestamp, salt):
        statement = select(cls).filter_by(server_url=server_url, timestamp=timestamp, salt=salt)
        if session.scalars(statement).first() is not None:
            return False
        cls(server_url=server_url, timestamp=timestamp, salt=salt).save()
        return True

    @classmethod
    def get(cls, server_url, salt):
        return session.scalars(select(cls).filter_by(server_url=server_url, salt=salt)).first()

    @classmethod
    def delete(cls, nonce) -> None:
        nonce.delete()


class FlaskAssociationMixin(AssociationMixin):
    @classmethod
    def store(cls, server_url, association) -> None:
        # Don't use get-or-create because issued cannot be null
        assoc = session.scalars(select(cls).filter_by(server_url=server_url, handle=association.handle)).first()
        if assoc is None:
            assoc = cls(server_url=server_url, handle=association.handle)

        assoc.secret = base64.encodebytes(association.secret).decode()
        assoc.issued = association.issued
        assoc.lifetime = association.lifetime
        assoc.assoc_type = association.assoc_type
        assoc.save()

    @classmethod
    def get(cls, *args, **kwargs) -> QuerySet:
        return QuerySet(select(cls).filter_by(**kwargs))

    @classmethod
    def remove(cls, ids_to_delete) -> None:
        QuerySet(select(cls).where(cls.id.in_(ids_to_delete))).delete()


class FlaskCodeMixin(CodeMixin):
    @classmethod
    def get_code(cls, code):
        return session.scalars(select(cls).filter_by(code=code)).first()


class FlaskPartialMixin(PartialMixin):
    @classmethod
    def load(cls, token):
        return session.scalars(select(cls).filter_by(token=token)).first()

    @classmethod
    def destroy(cls, token) -> None:
        partial = cls.load(token)
        if partial:
            partial.delete()


class BaseFlaskStorage(BaseStorage):
    user = FlaskUserMixin
    nonce = FlaskNonceMixin
    association = FlaskAssociationMixin
    code = FlaskCodeMixin

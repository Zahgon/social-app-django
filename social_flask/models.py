"""SQLAlchemy models for Social Auth"""

from __future__ import annotations

from typing import Any

from social_core.utils import module_member, setting_name
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, SaveMixin, session, utcnow
from .settings import get_setting_default
from .storage import (
    BaseFlaskStorage,
    FlaskAssociationMixin,
    FlaskCodeMixin,
    FlaskNonceMixin,
    FlaskPartialMixin,
    FlaskUserMixin,
)

UID_LENGTH = get_setting_default(setting_name("UID_LENGTH"), 255)
EMAIL_LENGTH = get_setting_default(setting_name("EMAIL_LENGTH"), 254)
NONCE_SERVER_URL_LENGTH = get_setting_default(setting_name("NONCE_SERVER_URL_LENGTH"), 255)
ASSOCIATION_SERVER_URL_LENGTH = get_setting_default(setting_name("ASSOCIATION_SERVER_URL_LENGTH"), 255)
ASSOCIATION_HANDLE_LENGTH = get_setting_default(setting_name("ASSOCIATION_HANDLE_LENGTH"), 255)
USERNAME_LENGTH = get_setting_default(setting_name("USERNAME_LENGTH"), 150)


class User(Base, SaveMixin):
    """Test-support user model.

    A Flask application normally brings its own user model and points
    ``SOCIAL_AUTH_USER_MODEL`` at its dotted path; this minimal model is the
    default so that the storage layer is usable (and testable) out of the box.
    """

    __tablename__ = "social_auth_user"

    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(USERNAME_LENGTH), unique=True)
    email: Mapped[str] = mapped_column(String(EMAIL_LENGTH), default="")
    password: Mapped[str] = mapped_column(String(128), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    first_name: Mapped[str] = mapped_column(String(150), default="")
    last_name: Mapped[str] = mapped_column(String(150), default="")

    social_auth: Mapped[list[UserSocialAuth]] = relationship(back_populates="user")

    def __str__(self) -> str:
        return self.username

    @property
    def is_authenticated(self) -> bool:
        return True

    def has_usable_password(self) -> bool:
        return bool(self.password)

    @classmethod
    def create_user(cls, username: str, email: str | None = None, password: str | None = None, **extra_fields):
        user = cls(username=username, email=email or "", password=password or "", **extra_fields)
        return user.save()


class AbstractUserSocialAuth(FlaskUserMixin):
    """Model level behaviour of the Social Auth association model."""

    @classmethod
    def get_social_auth(cls, provider: str, uid: str | int):
        if not isinstance(uid, str):
            uid = str(uid)
        for social in session.scalars(select(cls).filter_by(provider=provider, uid=uid)):
            # We need to compare to filter out case-insensitive lookups in
            # some databases (MySQL/MariaDB)
            if social.uid == uid:
                return social
        return None

    @classmethod
    def username_max_length(cls) -> int:
        username_field = cls.username_field()
        return cls.user_model().__table__.columns[username_field].type.length

    @classmethod
    def user_model(cls):
        path = get_setting_default(setting_name("USER_MODEL"), None)
        return module_member(path) if path else User


class UserSocialAuth(Base, SaveMixin, AbstractUserSocialAuth):
    """Social Auth association model"""

    __tablename__ = "social_auth_usersocialauth"
    __table_args__ = (UniqueConstraint("provider", "uid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("social_auth_user.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(32))
    uid: Mapped[str] = mapped_column(String(UID_LENGTH), index=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    created: Mapped[Any] = mapped_column(DateTime, default=utcnow)
    modified: Mapped[Any] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="social_auth")

    def __str__(self) -> str:
        return str(self.user)


class Nonce(Base, SaveMixin, FlaskNonceMixin):
    """One use numbers"""

    __tablename__ = "social_auth_nonce"
    __table_args__ = (UniqueConstraint("server_url", "timestamp", "salt"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    server_url: Mapped[str] = mapped_column(String(NONCE_SERVER_URL_LENGTH))
    timestamp: Mapped[int] = mapped_column(Integer)
    salt: Mapped[str] = mapped_column(String(65))


class Association(Base, SaveMixin, FlaskAssociationMixin):
    """OpenId account association"""

    __tablename__ = "social_auth_association"
    __table_args__ = (UniqueConstraint("server_url", "handle"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    server_url: Mapped[str] = mapped_column(String(ASSOCIATION_SERVER_URL_LENGTH))
    handle: Mapped[str] = mapped_column(String(ASSOCIATION_HANDLE_LENGTH))
    secret: Mapped[str] = mapped_column(String(255), default="")  # Stored base64 encoded
    issued: Mapped[int] = mapped_column(Integer, default=0)
    lifetime: Mapped[int] = mapped_column(Integer, default=0)
    assoc_type: Mapped[str] = mapped_column(String(64), default="")


class Code(Base, SaveMixin, FlaskCodeMixin):
    __tablename__ = "social_auth_code"
    __table_args__ = (UniqueConstraint("email", "code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(EMAIL_LENGTH))
    code: Mapped[str] = mapped_column(String(32), index=True, default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[Any] = mapped_column(DateTime, index=True, default=utcnow)


class Partial(Base, SaveMixin, FlaskPartialMixin):
    __tablename__ = "social_auth_partial"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(32), index=True, default="")
    next_step: Mapped[int] = mapped_column(SmallInteger, default=0)
    backend: Mapped[str] = mapped_column(String(32), default="")
    data: Mapped[dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    timestamp: Mapped[Any] = mapped_column(DateTime, index=True, default=utcnow)


class FlaskStorage(BaseFlaskStorage):
    user = UserSocialAuth
    nonce = Nonce
    association = Association
    code = Code
    partial = Partial

    @classmethod
    def is_integrity_error(cls, exception) -> bool:
        return isinstance(exception, IntegrityError)

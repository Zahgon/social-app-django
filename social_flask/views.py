from datetime import timedelta

from flask import Blueprint, abort, current_app, g
from flask import request as flask_request
from flask import session as flask_session
from social_core.actions import do_auth, do_complete, do_disconnect

from .utils import REDIRECT_FIELD_NAME, Storage, psa

social_auth = Blueprint("social", __name__, template_folder="templates")

# Setting the session expiry to ``None`` results in a session lifetime equal to
# the platform default session lifetime.
DEFAULT_SESSION_TIMEOUT = None

SESSION_USER_KEY = "_user_id"


def login_user(user) -> None:
    """Attach the given user to the current session."""
    flask_session[SESSION_USER_KEY] = str(user.id)
    flask_session.modified = True


def get_current_user():
    """Return the user attached to the current session, if any."""
    user_id = flask_session.get(SESSION_USER_KEY)
    if user_id is None:
        return None
    return Storage.user.get_user(pk=int(user_id))


def set_session_expiry(session_expiry) -> None:
    """Apply the computed session length to the current session."""
    if session_expiry is None:
        flask_session.permanent = False
        return
    current_app.permanent_session_lifetime = timedelta(seconds=session_expiry)
    flask_session.permanent = True


@social_auth.route("/login/<string:backend>", methods=["POST"], endpoint="begin")
@psa("social.complete")
def auth(backend):
    return do_auth(g.backend, redirect_name=REDIRECT_FIELD_NAME)


@social_auth.route("/complete/<string:backend>", methods=["GET", "POST"], endpoint="complete")
@psa("social.complete")
def complete(backend, *args, **kwargs):
    """Authentication complete view"""
    return do_complete(
        g.backend,
        _do_login,
        user=get_current_user(),
        redirect_name=REDIRECT_FIELD_NAME,
        request=flask_request._get_current_object(),  # noqa: SLF001
        *args,  # noqa: B026
        **kwargs,
    )


@social_auth.route("/disconnect/<string:backend>", methods=["POST"], endpoint="disconnect")
@social_auth.route(
    "/disconnect/<string:backend>/<int:association_id>",
    methods=["POST"],
    endpoint="disconnect_individual",
)
@psa()
def disconnect(backend, association_id=None):
    """Disconnects given backend from current logged in user."""
    user = get_current_user()
    if user is None:
        abort(401)
    return do_disconnect(g.backend, user, association_id, redirect_name=REDIRECT_FIELD_NAME)


def get_session_timeout(social_user, enable_session_expiration=False, max_session_length=None):
    if enable_session_expiration:
        # Retrieve an expiration date from the social user who just finished
        # logging in; this value was set by the social auth backend, and was
        # typically received from the server.
        expiration = social_user.expiration_datetime()

        # We've enabled session expiration. Check to see if we got
        # a specific expiration time from the provider for this user;
        # if not, use the platform default expiration.
        received_expiration_time = expiration.total_seconds() if expiration else DEFAULT_SESSION_TIMEOUT

        # Check to see if the backend set a value as a maximum length
        # that a session may be; if they did, then we should use the minimum
        # of that and the received session expiration time, if any, to
        # set the session length.
        if received_expiration_time is None and max_session_length is None:
            # We neither received an expiration length, nor have a maximum
            # session length. Use the platform default.
            session_expiry = DEFAULT_SESSION_TIMEOUT
        elif received_expiration_time is None and max_session_length is not None:
            # We only have a maximum session length; use that.
            session_expiry = max_session_length
        elif received_expiration_time is not None and max_session_length is None:
            # We only have an expiration time received by the backend
            # from the provider, with no set maximum. Use that.
            session_expiry = received_expiration_time
        else:
            # We received an expiration time from the backend, and we also
            # have a set maximum session length. Use the smaller of the two.
            session_expiry = min(received_expiration_time, max_session_length)
    # If there's an explicitly-set maximum session length, use that
    # even if we don't want to retrieve session expiry times from
    # the backend. If there isn't, then use the platform default.
    elif max_session_length is None:
        session_expiry = DEFAULT_SESSION_TIMEOUT
    else:
        session_expiry = max_session_length

    return session_expiry


def _do_login(backend, user, social_user) -> None:
    user.backend = f"{backend.__module__}.{backend.__class__.__name__}"
    # Get these details early to avoid any issues involved in the
    # session switch that happens when we call login_user().
    enable_session_expiration = backend.setting("SESSION_EXPIRATION", False)
    max_session_length_setting = backend.setting("MAX_SESSION_LENGTH", None)

    # Log the user in.
    login_user(user)

    # Make sure that the max_session_length value is either an integer or
    # None. Because we get this as a setting from the backend, it can be set
    # to whatever the backend creator wants; we want to be resilient against
    # unexpected types being presented to us.
    try:
        max_session_length = int(max_session_length_setting)
    except (TypeError, ValueError):
        # We got a response that doesn't look like a number; use the default.
        max_session_length = None

    # Get the session expiration length based on the maximum session length
    # setting, combined with any session length received from the backend.
    session_expiry = get_session_timeout(
        social_user,
        enable_session_expiration=enable_session_expiration,
        max_session_length=max_session_length,
    )

    try:
        # Set the session length to our previously determined expiry length.
        set_session_expiry(session_expiry)
    except OverflowError:
        # The timestamp we used wasn't in the range of values supported for
        # a session length; use the platform default. We tried.
        set_session_expiry(DEFAULT_SESSION_TIMEOUT)

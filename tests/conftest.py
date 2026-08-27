import os

import pytest
from flask import Flask, Request
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from werkzeug.formparser import FormDataParser

from social_flask import init_app
from social_flask.db import session as db_session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

SECRET_KEY = "6p%gef2(6kvjsgl*7!51a7z8c3=u4uc&6ulpua0g1^&sthiifp"  # noqa: S105


class StrictFormDataParser(FormDataParser):
    """Surface malformed form payloads instead of silently ignoring them.

    Werkzeug parses form data leniently by default; Django raises. Being
    strict keeps the ported behaviour (and the guards that depend on it)
    observable.
    """

    def __init__(self, *args, **kwargs) -> None:
        kwargs["silent"] = False
        super().__init__(*args, **kwargs)


class StrictRequest(Request):
    form_data_parser_class = StrictFormDataParser


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    engine.dispose()


@pytest.fixture
def app(engine):
    db_session.remove()
    application = Flask("tests", template_folder=TEMPLATES_DIR)
    application.request_class = StrictRequest
    # Jinja2 drops a template's trailing newline by default; Django's engine
    # keeps it. Preserve it so rendering is byte-faithful to the template file.
    application.jinja_options = {"keep_trailing_newline": True}
    application.config.update(
        TESTING=True,
        SECRET_KEY=SECRET_KEY,
        SERVER_NAME="testserver",
        # Django's default LOGIN_REDIRECT_URL, kept as the test app default.
        LOGIN_REDIRECT_URL="/accounts/profile/",
        AUTHENTICATION_BACKENDS=["social_core.backends.facebook.FacebookOAuth2"],
    )
    init_app(application, engine)
    with application.app_context():
        yield application
    db_session.remove()


@pytest.fixture
def client(app):
    return app.test_client()

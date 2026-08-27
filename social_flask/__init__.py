import importlib.metadata

try:
    __version__ = importlib.metadata.version("social-auth-app-flask")
except importlib.metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"


def init_app(app, engine, url_prefix: str = "") -> None:
    """Wire Social Auth into the given Flask application.

    Binds the shared SQLAlchemy session to ``engine``, registers the blueprint,
    the exception handler and the context processors, and installs a default
    strategy for backends instantiated without one.
    """
    from social_core.registry import REGISTRY  # noqa: PLC0415

    from .clearsocial import register_cli  # noqa: PLC0415
    from .context_processors import backends, login_redirect  # noqa: PLC0415
    from .db import init_social  # noqa: PLC0415
    from .middleware import register_exception_handler  # noqa: PLC0415
    from .utils import load_strategy  # noqa: PLC0415
    from .views import social_auth  # noqa: PLC0415

    init_social(app, engine)
    app.register_blueprint(social_auth, url_prefix=url_prefix)
    register_exception_handler(app)
    app.context_processor(backends)
    app.context_processor(login_redirect)
    register_cli(app)

    # social_core instantiates backends without arguments in some code paths;
    # give those a usable default strategy.
    REGISTRY.default_strategy = load_strategy(request=None)

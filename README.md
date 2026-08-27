# Python Social Auth - Flask

Python Social Auth is an easy to setup social authentication/registration
mechanism with support for several frameworks and auth providers.

## Description

This is the [Flask](https://flask.palletsprojects.com/) component of the
[python-social-auth ecosystem](https://github.com/python-social-auth/social-core),
it implements the needed functionality to integrate
[social-auth-core](https://github.com/python-social-auth/social-core)
in a Flask based project.

Persistence uses plain [SQLAlchemy](https://www.sqlalchemy.org/) 2.0 with a
`scoped_session`, so the storage classmethods keep working outside of a
request or application context.

## Flask version

This project targets Flask 3.0 and newer.

Backward compatibility with unsupported versions won't be enforced.

## Documentation

Project documentation is available at https://python-social-auth.readthedocs.io/.

## Setup

```shell
$ pip install social-auth-app-flask
```

```python
from flask import Flask
from sqlalchemy import create_engine

from social_flask import init_app

app = Flask(__name__)
app.config["AUTHENTICATION_BACKENDS"] = ["social_core.backends.github.GithubOAuth2"]
init_app(app, create_engine("sqlite:///social.db"))
```

## Contributing

Contributions are welcome!

Only the core and Flask modules are currently in development. All others are in maintenance only mode, and maintainers are especially welcome there.

See the [CONTRIBUTING.md](https://github.com/python-social-auth/.github/blob/main/CONTRIBUTING.md) document for details.

## Versioning

This project follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## License

This project follows the BSD license. See the [LICENSE](LICENSE) for details.

## Donations

This project welcomes donations to make the development sustainable, you can fund Python Social Auth on following platforms:

- [GitHub Sponsors](https://github.com/sponsors/python-social-auth/)
- [Open Collective](https://opencollective.com/python-social-auth)

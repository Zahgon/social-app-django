from social_flask.context_processors import login_redirect


class TestContextProcessors:
    def test_login_redirect_unicode_quote(self, app):
        with app.test_request_context("/", query_string={"next": "profile/sjó"}):
            result = login_redirect()
        assert result == {
            "REDIRECT_FIELD_NAME": "next",
            "REDIRECT_FIELD_VALUE": "profile/sj%C3%B3",
            "REDIRECT_QUERYSTRING": "next=profile/sj%C3%B3",
        }

    def test_login_redirect_malformed_post(self, app):
        with app.test_request_context(
            "/",
            method="POST",
            data="no boundary",
            content_type="multipart/form-data",
        ):
            result = login_redirect()
        assert result == {
            "REDIRECT_FIELD_NAME": "next",
            "REDIRECT_FIELD_VALUE": None,
            "REDIRECT_QUERYSTRING": "",
        }

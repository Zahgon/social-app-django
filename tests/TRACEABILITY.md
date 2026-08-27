# Test traceability — Django suite → Flask/pytest suite

Baseline: `social-app-django` @ tag `6.0.1` (commit `6ab4a22`), **89 passed, 1 warning**.
Ported: **81 passed** with `.venv-sad-flask/bin/python -m pytest tests/ -q`.

89 baseline tests − 8 scoped-out tests = 81 ported tests. Every scoped-out test is
enumerated below with the concrete reason it cannot exist against Flask.

## 1. Ported

| Original Django test | Ported pytest node |
| --- | --- |
| `tests/test_models.py::TestSocialAuthUser::test_user_relationship_none` | `tests/test_models.py::TestSocialAuthUser::test_user_relationship_none` |
| `tests/test_models.py::TestSocialAuthUser::test_user_existing_relationship` | `tests/test_models.py::TestSocialAuthUser::test_user_existing_relationship` |
| `tests/test_models.py::TestSocialAuthUser::test_get_social_auth` | `tests/test_models.py::TestSocialAuthUser::test_get_social_auth` |
| `tests/test_models.py::TestSocialAuthUser::test_get_social_auth_none` | `tests/test_models.py::TestSocialAuthUser::test_get_social_auth_none` |
| `tests/test_models.py::TestSocialAuthUser::test_cleanup` | `tests/test_models.py::TestSocialAuthUser::test_cleanup` (`call_command("clearsocial")` → `social_flask.clearsocial.clearsocial()`) |
| `tests/test_models.py::TestUserSocialAuth::test_changed` | `tests/test_models.py::TestUserSocialAuth::test_changed` |
| `tests/test_models.py::TestUserSocialAuth::test_set_extra_data` | `tests/test_models.py::TestUserSocialAuth::test_set_extra_data` (`refresh_from_db()` → `db_session.expire()`) |
| `tests/test_models.py::TestUserSocialAuth::test_disconnect` | `tests/test_models.py::TestUserSocialAuth::test_disconnect` |
| `tests/test_models.py::TestUserSocialAuth::test_username_field` | `tests/test_models.py::TestUserSocialAuth::test_username_field` |
| `tests/test_models.py::TestUserSocialAuth::test_user_exists` | `tests/test_models.py::TestUserSocialAuth::test_user_exists` |
| `tests/test_models.py::TestUserSocialAuth::test_get_username` | `tests/test_models.py::TestUserSocialAuth::test_get_username` |
| `tests/test_models.py::TestUserSocialAuth::test_create_user` | `tests/test_models.py::TestUserSocialAuth::test_create_user` |
| `tests/test_models.py::TestUserSocialAuth::test_create_user_reraise` | `tests/test_models.py::TestUserSocialAuth::test_create_user_reraise` |
| `tests/test_models.py::TestUserSocialAuth::test_create_user_custom_username` | `tests/test_models.py::TestUserSocialAuth::test_create_user_custom_username` (`UserManager.create_user` → `social_flask.models.User.create_user`) |
| `tests/test_models.py::TestUserSocialAuth::test_create_user_existing` | `tests/test_models.py::TestUserSocialAuth::test_create_user_existing` (`django.db.IntegrityError` → `sqlalchemy.exc.IntegrityError`) |
| `tests/test_models.py::TestUserSocialAuth::test_get_user` | `tests/test_models.py::TestUserSocialAuth::test_get_user` |
| `tests/test_models.py::TestUserSocialAuth::test_get_users_by_email` | `tests/test_models.py::TestUserSocialAuth::test_get_users_by_email` (`override_settings` → `app.config`) |
| `tests/test_models.py::TestUserSocialAuth::test_get_social_auth` | `tests/test_models.py::TestUserSocialAuth::test_get_social_auth` (model + mixin layers; see scope-out S6 for the manager layer) |
| `tests/test_models.py::TestUserSocialAuth::test_get_social_auth_int_uid` | `tests/test_models.py::TestUserSocialAuth::test_get_social_auth_int_uid` |
| `tests/test_models.py::TestUserSocialAuth::test_get_social_auth_for_user` | `tests/test_models.py::TestUserSocialAuth::test_get_social_auth_for_user` |
| `tests/test_models.py::TestUserSocialAuth::test_create_social_auth` | `tests/test_models.py::TestUserSocialAuth::test_create_social_auth` |
| `tests/test_models.py::TestUserSocialAuth::test_username_max_length` | `tests/test_models.py::TestUserSocialAuth::test_username_max_length` |
| `tests/test_models.py::TestNonce::test_use` | `tests/test_models.py::TestNonce::test_use` |
| `tests/test_models.py::TestAssociation::test_store_get_remove` | `tests/test_models.py::TestAssociation::test_store_get_remove` |
| `tests/test_models.py::TestCode::test_get_code` | `tests/test_models.py::TestCode::test_get_code` |
| `tests/test_models.py::TestPartial::test_load_destroy` | `tests/test_models.py::TestPartial::test_load_destroy` |
| `tests/test_models.py::TestDjangoStorage::test_is_integrity_error` | `tests/test_models.py::TestFlaskStorage::test_is_integrity_error` |
| `tests/test_storage_integration.py::TestStorageIntegration::test_openid_store_association_workflow` | same node |
| `tests/test_storage_integration.py::TestStorageIntegration::test_openid_store_association_expiration` | same node |
| `tests/test_storage_integration.py::TestStorageIntegration::test_openid_store_multiple_associations` | same node |
| `tests/test_storage_integration.py::TestStorageIntegration::test_openid_store_nonce_workflow` | same node |
| `tests/test_storage_integration.py::TestStorageIntegration::test_openid_store_nonce_timestamp_skew` | same node |
| `tests/test_storage_integration.py::TestAssociationMixinIntegration::test_oids_method` | same node |
| `tests/test_storage_integration.py::TestAssociationMixinIntegration::test_oids_method_with_handle` | same node |
| `tests/test_storage_integration.py::TestAssociationMixinIntegration::test_get_method` | same node |
| `tests/test_storage_integration.py::TestNonceMixinIntegration::test_use_method` | same node |
| `tests/test_storage_integration.py::TestNonceMixinIntegration::test_get_method` | same node |
| `tests/test_storage_integration.py::TestNonceMixinIntegration::test_delete_method` | same node |
| `tests/test_strategy.py::TestStrategy::test_request_methods` | `tests/test_strategy.py::TestStrategy::test_request_methods` (`QueryDict` → `werkzeug.datastructures.MultiDict`) |
| `tests/test_strategy.py::TestStrategy::test_build_absolute_uri` | same node (`http://testserver/`) |
| `tests/test_strategy.py::TestStrategy::test_settings` | same node (`gettext_lazy("/")` → `LazyURL("/")`, a lazily evaluated URL setting) |
| `tests/test_strategy.py::TestStrategy::test_session_methods` | same node |
| `tests/test_strategy.py::TestStrategy::test_random_string` | same node |
| `tests/test_strategy.py::TestStrategy::test_session_value` | same node (`ContentType` pk → dotted model path string identity) |
| `tests/test_strategy.py::TestStrategy::test_session_value_flattens_request_data` | same node |
| `tests/test_strategy.py::TestStrategy::test_get_language` | same node (`en-us`) |
| `tests/test_strategy.py::TestStrategy::test_html` | same node (`HttpResponse.content` → `flask.Response.data`) |
| `tests/test_strategy.py::TestStrategy::test_partial_pipeline_external_resume_confirmation` | same node |
| `tests/test_strategy.py::TestStrategy::test_partial_pipeline_external_resume_confirmation_uses_custom_parameter` | same node |
| `tests/test_strategy.py::TestStrategy::test_partial_pipeline_external_resume_confirmed` | same node |
| `tests/test_strategy.py::TestStrategy::test_partial_pipeline_external_resume_confirmed_uses_custom_parameter` | same node |
| `tests/test_strategy.py::TestStrategy::test_partial_pipeline_external_resume_confirmation_without_request` | same node |
| `tests/test_strategy.py::TestStrategy::test_partial_pipeline_external_resume_confirmed_without_request` | same node |
| `tests/test_strategy.py::TestStrategy::test_partial_pipeline_external_resume_confirmation_rejects_get` | same node |
| `tests/test_strategy.py::TestStrategy::test_partial_pipeline_external_resume_confirmation_rejects_missing_parameter` | same node |
| `tests/test_strategy.py::TestStrategy::test_partial_pipeline_external_resume_confirmation_rejects_missing_nonce` | same node |
| `tests/test_strategy.py::TestStrategy::test_partial_pipeline_external_resume_confirmation_rejects_wrong_nonce` | same node |
| `tests/test_strategy.py::TestStrategy::test_authenticate` | same node (`result.backend == "social_core.backends.facebook.FacebookOAuth2"`) |
| `tests/test_strategy.py::TestStrategy::test_clean_authenticate_args` | same node |
| `tests/test_strategy.py::TestStrategy::test_clean_authenticate_args_none` | same node |
| `tests/test_strategy.py::TestStrategy::test_session_creation_without_request` | same node |
| `tests/test_views.py::TestViews::test_begin_view` | same node (`reverse("social:begin")` → `url_for("social.begin")`) |
| `tests/test_views.py::TestViews::test_begin_view_requires_post` | same node (405) |
| `tests/test_views.py::TestViews::test_complete` | same node (`SessionBase.set_expiry` → `social_flask.views.set_session_expiry`, `OverflowError` then `None`; 302 → `/accounts/profile/`) |
| `tests/test_views.py::TestViews::test_disconnect` | same node (`client.login()` → session `_user_id`; `AbstractBaseUser.has_usable_password` → `social_flask.models.User.has_usable_password`) |
| `tests/test_views.py::TestGetSessionTimeout::test_expiration_disabled_no_max` | same node (`None`) |
| `tests/test_views.py::TestGetSessionTimeout::test_expiration_disabled_with_max` | same node (`60`) |
| `tests/test_views.py::TestGetSessionTimeout::test_expiration_disabled_with_zero_max` | same node (`0`) |
| `tests/test_views.py::TestGetSessionTimeout::test_user_has_session_length_no_max` | same node (`60`) |
| `tests/test_views.py::TestGetSessionTimeout::test_user_has_session_length_larger_max` | same node (`60`) |
| `tests/test_views.py::TestGetSessionTimeout::test_user_has_session_length_smaller_max` | same node (`30`) |
| `tests/test_views.py::TestGetSessionTimeout::test_user_has_no_session_length_with_max` | same node (`60`) |
| `tests/test_views.py::TestGetSessionTimeout::test_user_has_no_session_length_no_max` | same node (`None`) |
| `tests/test_context_processors.py::TestContextProcessors::test_login_redirect_unicode_quote` | same node (`profile/sj%C3%B3`) |
| `tests/test_context_processors.py::TestContextProcessors::test_login_redirect_malformed_post` | same node (malformed multipart → `None`) |
| `tests/test_middleware.py::TestMiddleware::test_exception` | same node (no `LOGIN_ERROR_URL` → exception propagates) |
| `tests/test_middleware.py::TestMiddleware::test_exception_debug` | same node (`DEBUG=True` → `RAISE_EXCEPTIONS`) |
| `tests/test_middleware.py::TestMiddleware::test_login_error_url` | same node (`/`) |
| `tests/test_middleware.py::TestMiddleware::test_message_failure` | same node (`django.contrib.messages.error`/`MessageFailure` → `flask.flash`/`RuntimeError`; `/?message=Authentication%20process%20canceled&backend=facebook`) |
| `tests/test_middleware.py::TestMiddleware::test_backend_specific_login_error_url` | same node (`/facebook-error`) |
| `tests/test_middleware.py::TestMiddleware::test_backend_specific_raise_exceptions` | same node |

## 2. Scoped out

Each entry names a Django framework capability with no Flask counterpart. No
in-scope assertion is hidden here.

| ID | Removed test / assertion | Why it cannot exist in Flask |
| --- | --- | --- |
| S1 | `tests/test_admin.py::SocialAdminTest::test_admin_app_name` (`assertContains(response, "Python Social Auth")`) | Asserts the verbose app name rendered by `django.contrib.admin`'s index page. Flask ships no admin site, and `social_flask` has no `admin.py` / `AppConfig` to name. |
| S2 | `tests/test_admin.py::SocialAdminTest::test_social_auth_changelist` (GET `admin:social_django_usersocialauth_changelist`) | Asserts a `django.contrib.admin` changelist route generated from `Model._meta`. No admin site, no `_meta`, no generated route in Flask. |
| S3 | `tests/test_migrations.py::PendingMigrationsTests::test_no_pending_migrations` (`makemigrations --dry-run --check` produces nothing) | Asserts the Django migration graph matches the models. `social_flask` has no migration graph: the schema is created with `Base.metadata.create_all()`. |
| S4 | `tests/test_middleware.py::TestMiddleware::test_sync_middleware` (`middleware(request) is expected`, `get_response.assert_called_once_with(request)`, `iscoroutinefunction(middleware) is False`) | Asserts Django's middleware **object protocol** (`__init__(get_response)` / `__call__(request)`). Flask has no middleware object in the WSGI dispatch path; the equivalent is `app.register_error_handler`, which has no `get_response` chain to assert on. The behaviour this test guards — a synchronous exception turning into a redirect — remains fully covered by `test_login_error_url`, `test_message_failure`, `test_backend_specific_login_error_url`, `test_exception`, `test_exception_debug` and `test_backend_specific_raise_exceptions`. |
| S5 | `tests/test_middleware.py::TestMiddleware::test_async_middleware` (`await middleware(request) is expected`, `iscoroutinefunction(middleware) is True`) | Asserts `asgiref`/`sync_and_async_middleware` dual-protocol support. Flask 3 is WSGI and `asgiref` was removed from the dependencies; there is no coroutine middleware object to mark. |
| S6 | `tests/test_models.py::TestUserSocialAuth::test_get_social_auth` — the two "Manager" assertions (`UserSocialAuth.objects.get_social_auth(...) == usa` and `... is None`) | Assert `social_django.managers.UserSocialAuthManager`, i.e. Django's `Model.objects` manager protocol. SQLAlchemy has no manager object; the same lookup is reached through the model classmethod and the mixin classmethod, both of which **are** asserted in the ported test. The sibling test `test_get_social_auth_int_uid` keeps all three of its blocks (its "Manager" block calls the same classmethod), with the third routed through `FlaskStorage.user`. |
| S7 | `tests/test_strategy.py::TestStrategy::test_get_session_id_creates_session` (`session.session_key` is `None`, then `session.exists(session_id)`) | Asserts Django's server-side session store (`SESSION_ENGINE`, `SessionStore.session_key`, `.exists()`). Flask's default session interface is a stateless signed cookie: there is no session key and no server-side store to look one up in, and no server-side session backend is in the dependency set (`Flask`, `SQLAlchemy`, `blinker`, `social-auth-core`). `FlaskStrategy` therefore keeps `BaseStrategy.get_session_id()`, which returns `None`. |
| S8 | `tests/test_strategy.py::TestStrategy::test_get_session_id_reuses_existing_session` (`session.create()` then `get_session_id() == session_key`) | Same root cause as S7: `SessionStore.create()` and session-key reuse only exist for a server-side session backend. |
| S9 | `tests/test_strategy.py::TestStrategy::test_new_session_can_be_restored_without_cookie` (`restore_session(session_id, {})` then `session_get("saml_authn_request_id") == "TEST_ID"` and key rotation) | Same root cause as S7. `BaseStrategy.restore_session` raises `StrategyMissingFeatureError` by default and `FlaskStrategy` does not override it, because restoring a session by id and rotating its key both require a server-side store. |

Count: S1–S5 and S7–S9 remove 8 test methods (89 − 8 = 81). S6 removes 2
assertions from a test that is otherwise ported in full.

No in-scope assertion was weakened, deleted, or made to pass by special-casing.

# Testing

SmartMeet uses two types of automated tests: unit tests and Selenium system tests.

---

## Test Structure

tests/
├── unit/
│   └── test_routes.py       # Unit tests for authentication and validation logic
└── selenium/
└── test_workflow.py     # End-to-end browser tests for user workflows

---

## Running the Tests

### Unit tests

```bash
python -m pytest tests/unit
```

### Selenium tests

```bash
python -m pytest tests/selenium
```

### All tests

```bash
python -m pytest tests/
```

---

## Unit Tests

Unit tests are written using `pytest` and Flask's built-in test client. They run entirely in memory using an isolated SQLite database — the real `smartmeet.db` is never touched.

### Test database isolation

The app is initialised with `TestConfig` which sets:

```python
class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True
```

- `sqlite:///:memory:` — creates a fresh in-memory database for each test, destroyed when the test ends
- `WTF_CSRF_ENABLED = False` — disables CSRF tokens so form submissions work in tests
- `MAIL_SUPPRESS_SEND = True` — stops any emails from actually being sent during tests

### What is tested

| Test | What it checks |
|------|----------------|
| `test_login_page_loads_correctly` | GET /login returns 200 |
| `test_login_with_correct_credentials_succeeds` | Valid login redirects to index |
| `test_login_with_wrong_password_shows_error_message` | Invalid login shows error |
| `test_signup_with_duplicate_username_is_rejected` | Duplicate username shows error |
| `test_signup_with_weak_password_is_rejected` | Weak password shows error |
| `test_signup_with_mismatched_passwords_is_rejected` | Mismatched passwords shows error |
| `test_signup_with_missing_fields_shows_error` | Missing fields shows error |
| `test_dashboard_redirects_to_login_when_not_authenticated` | Protected route redirects unauthenticated users |
| `test_results_page_redirects_to_login_when_not_authenticated` | Protected route redirects unauthenticated users |
| `test_user_password_is_hashed_in_database` | Passwords are never stored in plaintext |

---

## Selenium Tests

Selenium tests use a real Chrome browser to test end-to-end user workflows. The test suite automatically starts a Flask server using `TestConfig` before the tests run and shuts it down after.

### Requirements

- Google Chrome must be installed
- `selenium` and `webdriver-manager` must be installed (included in `requirements.txt`)
- `webdriver-manager` handles downloading the correct ChromeDriver automatically

### How the server is started

The server is started in a background thread before any tests run:

```python
thread = threading.Thread(
    target=lambda: app.run(host='127.0.0.1', port=5000, use_reloader=False)
)
thread.daemon = True
thread.start()
```

`threading` is used instead of `multiprocessing` for cross-platform compatibility — `multiprocessing` with local functions causes a `PicklingError` on Windows.

### Test user

A single test user is seeded into the in-memory database before the tests run:

| Username | Password | Display Name |
|----------|----------|--------------|
| testuser1 | Test123! | Alice |

### What is tested

| Test | What it checks |
|------|----------------|
| `test_landing_page_loads_and_has_correct_title` | Homepage loads with correct title |
| `test_login_with_predefined_test_account_succeeds` | Valid login redirects to index |
| `test_login_with_wrong_password_shows_error_message` | Invalid login shows error message |
| `test_dashboard_is_accessible_after_successful_login` | Dashboard loads after login |
| `test_dashboard_redirects_to_login_when_unauthenticated` | Dashboard redirects unauthenticated users |
| `test_logout_works_and_protected_pages_redirect_to_login` | Logout works and session is cleared |
| `test_signup_page_loads_correctly` | Signup page loads |
| `test_signup_with_weak_password_shows_error_message` | Weak password shows error |
| `test_friends_page_loads_after_login` | Friends page loads after login |
| `test_settings_page_loads_after_login` | Settings page loads after login |

### Notes

- Tests run in headless Chrome (no browser window appears)
- Each test gets a fresh browser instance so there is no shared state between tests
- The server runs on `http://localhost:5000` during testing
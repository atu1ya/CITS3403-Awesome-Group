# Testing

SmartMeet uses two types of automated tests: unit tests and Selenium system tests.

---

## Test Structure
tests/
├── unit/
│   └── test_routes.py       # Unit tests for authentication, validation, rooms, friends and results
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
| `test_create_event_saves_room_and_redirects_to_availability` | Room creation saves to database and redirects correctly |
| `test_unassociated_user_cannot_submit_availability` | Unauthorised users cannot submit availability (403) |
| `test_successful_availability_submission_creates_rows_and_updates_status` | Availability submission saves correctly and updates participant status |
| `test_add_friend_creates_pending_friendship` | Friend request creates a pending friendship |
| `test_accept_friend_marks_friendship_accepted` | Accepting a friend request updates status to accepted |
| `test_remove_friend_deletes_friendship_row` | Removing a friend deletes the friendship row |
| `test_user_search_returns_matching_users` | User search returns correct results |
| `test_results_page_aggregates_scores_and_orders_best_slots` | Results heatmap scores and orders slots correctly |
| `test_confirm_time_records_confirmed_slot` | Confirming a time saves the confirmed slot |
| `test_notify_participants_records_suggested_slot` | Notifying participants saves the suggested slot |

---

## Selenium Tests

Selenium tests use a real Chrome browser to test end-to-end user workflows. The test suite automatically starts a Flask server before the tests run and shuts it down after.

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

### Test database

The Selenium tests use a temporary file-based SQLite database (instead of in-memory) to allow the server thread to share state with the test setup. The following users and data are seeded before the tests run:

| Username | Password | Display Name | Role |
|----------|----------|--------------|------|
| testuser1 | Test123! | Alice | Organiser / main test user |
| bob | Test123! | Bob | Friend target |

A seeded room with availability data is also created for the results workflow tests.

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
| `test_create_event_and_availability_workflow` | Full room creation and availability submission end-to-end |
| `test_friends_interaction_workflow` | Sending a friend request in the browser |
| `test_results_presentation_workflow` | Results page loads heatmap and displays correct best slot |

### Notes

- Tests run in headless Chrome (no browser window appears)
- Each test gets a fresh browser instance so there is no shared state between tests
- The server runs on `http://localhost:5000` during testing
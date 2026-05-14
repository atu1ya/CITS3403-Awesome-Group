import pytest
from werkzeug.security import generate_password_hash
from sqlalchemy.pool import StaticPool

from app import create_app, db
from app.models import User


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_ENGINE_OPTIONS={
            'connect_args': {'check_same_thread': False},
            'poolclass': StaticPool,
        },
    )

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def create_user(username='testuser1', email='test1@smartmeet.com', password='Test123!', display_name='Alice'):
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        display_name=display_name,
    )
    db.session.add(user)
    db.session.commit()
    return user


def login(client, identifier='testuser1', password='Test123!'):
    return client.post(
        '/login',
        data={'identifier': identifier, 'password': password},
        follow_redirects=False,
    )


def test_login_page_loads_correctly(client):
    response = client.get('/login')
    assert response.status_code == 200


def test_login_with_correct_credentials_succeeds(client):
    with client.application.app_context():
        create_user()

    response = login(client)
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/dashboard')


def test_login_with_wrong_password_shows_error_message(client):
    with client.application.app_context():
        create_user()

    response = login(client, password='WrongPass1!')
    assert response.status_code == 200
    assert b'Invalid username or password.' in response.data


def test_signup_with_duplicate_username_is_rejected(client):
    with client.application.app_context():
        create_user()

    response = client.post(
        '/signup',
        data={
            'display_name': 'Bob',
            'username': 'testuser1',
            'email': 'bob@example.com',
            'password': 'Test123!',
            'confirm': 'Test123!',
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b'Username already taken.' in response.data


def test_signup_with_weak_password_is_rejected(client):
    response = client.post(
        '/signup',
        data={
            'display_name': 'Bob',
            'username': 'newuser',
            'email': 'bob@example.com',
            'password': 'weak',
            'confirm': 'weak',
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b'Password must be at least 8 characters.' in response.data


def test_dashboard_redirects_to_login_when_not_authenticated(client):
    response = client.get('/dashboard', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_signup_with_mismatched_passwords_is_rejected(client):
    response = client.post(
        '/signup',
        data={
            'display_name': 'Bob',
            'username': 'newuser2',
            'email': 'bob2@example.com',
            'password': 'Test123!',
            'confirm': 'Test123?'
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b'Passwords do not match.' in response.data


def test_results_page_redirects_to_login_when_not_authenticated(client):
    response = client.get('/results', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_user_password_is_hashed_in_database(client):
    with client.application.app_context():
        user = User(
            username='hashcheck',
            email='hashcheck@example.com',
            password_hash=generate_password_hash('Test123!'),
            display_name='Hash Check',
        )
        db.session.add(user)
        db.session.commit()

        stored_user = User.query.filter_by(username='hashcheck').first()
        assert stored_user is not None
        assert stored_user.password_hash != 'Test123!'
        assert stored_user.password_hash.startswith('pbkdf2:') or stored_user.password_hash.startswith('scrypt:')


def test_signup_with_missing_fields_shows_error(client):
    response = client.post(
        '/signup',
        data={
            'display_name': '',
            'username': 'missingfields',
            'email': '',
            'password': 'Test123!',
            'confirm': 'Test123!',
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b'Please fill in all fields.' in response.data
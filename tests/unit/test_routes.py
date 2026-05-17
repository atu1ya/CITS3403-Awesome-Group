import re
from datetime import date

import pytest
from sqlalchemy.pool import StaticPool
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Availability, Friendship, Room, RoomParticipant, User
from config import TestConfig


@pytest.fixture()
def client():
    app = create_app(TestConfig)
    app.config.update(
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


def create_room(
    organiser,
    title='Planning Session',
    description='Weekly team planning',
    date_from=date(2026, 5, 17),
    date_to=date(2026, 5, 18),
    time_start='9:00 AM',
    time_end='10:00 AM',
    duration='30 min',
):
    room = Room(
        title=title,
        description=description,
        date_from=date_from,
        date_to=date_to,
        selected_dates=f'{date_from:%Y-%m-%d},{date_to:%Y-%m-%d}',
        time_start=time_start,
        time_end=time_end,
        duration=duration,
        organiser_id=organiser.id,
    )
    db.session.add(room)
    db.session.flush()
    return room


def test_login_page_loads_correctly(client):
    response = client.get('/login')
    assert response.status_code == 200


def test_login_with_correct_credentials_succeeds(client):
    with client.application.app_context():
        create_user()
    response = login(client)
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/')


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
            'confirm': 'Test123?',
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
        create_user(username='hashcheck', email='hashcheck@example.com')
        stored_user = User.query.filter_by(username='hashcheck').first()
        assert stored_user is not None
        assert stored_user.password_hash != 'Test123!'
        assert (stored_user.password_hash.startswith('pbkdf2:')
                or stored_user.password_hash.startswith('scrypt:'))


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


def test_create_event_saves_room_and_redirects_to_availability(client):
    with client.application.app_context():
        organiser = create_user(username='organiser', email='organiser@example.com')
        organiser_id = organiser.id
    login(client, identifier='organiser')

    response = client.post(
        '/create-event',
        data={
            'roomName': 'Sprint Planning',
            'roomDesc': 'Weekly sprint planning session',
            'dateFrom': '2026-05-17',
            'dateTo': '2026-05-18',
            'timeStart': '9:00 AM',
            'timeEnd': '10:00 AM',
            'duration': '30 min',
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert '/availability/' in response.headers['Location']

    with client.application.app_context():
        room = Room.query.filter_by(title='Sprint Planning').first()
        assert room is not None
        assert room.organiser_id == organiser_id
        assert room.description == 'Weekly sprint planning session'


def test_unassociated_user_cannot_submit_availability(client):
    with client.application.app_context():
        organiser = create_user(username='organiser2', email='organiser2@example.com')
        create_user(username='visitor', email='visitor@example.com')
        room = create_room(organiser)
        db.session.commit()
        room_code = room.code

    login(client, identifier='visitor')
    response = client.post(
        f'/availability/{room_code}/submit',
        data={'tile_2026-05-17_9_00_AM': 'free'},
        follow_redirects=False,
    )

    assert response.status_code == 403


def test_successful_availability_submission_creates_rows_and_updates_status(client):
    with client.application.app_context():
        organiser = create_user(username='organiser3', email='organiser3@example.com')
        participant = create_user(username='participant', email='participant@example.com')
        room = create_room(organiser)
        db.session.add(RoomParticipant(room_id=room.id, user_id=participant.id, status='invited'))
        db.session.commit()
        room_code = room.code
        room_id = room.id
        participant_id = participant.id

    login(client, identifier='participant')
    response = client.post(
        f'/availability/{room_code}/submit',
        data={'tile_2026-05-17_9_00_AM': 'free'},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/dashboard')

    with client.application.app_context():
        saved = Availability.query.filter_by(room_id=room_id, user_id=participant_id).all()
        assert len(saved) == 1
        assert saved[0].time_slot == '2026-05-17 9:00 AM'
        assert saved[0].status == 'free'
        updated_participant = RoomParticipant.query.filter_by(room_id=room_id, user_id=participant_id).first()
        assert updated_participant is not None
        assert updated_participant.status == 'awaiting'


def test_add_friend_creates_pending_friendship(client):
    with client.application.app_context():
        create_user(username='alice', email='alice@example.com')
        create_user(username='bob', email='bob@example.com', display_name='Bob')

    login(client, identifier='alice')
    response = client.post('/friends/add', data={'username': 'bob'}, follow_redirects=False)

    assert response.status_code == 302
    with client.application.app_context():
        friendship = Friendship.query.filter_by(status='pending').first()
        assert friendship is not None
        assert friendship.sender.username == 'alice'
        assert friendship.receiver.username == 'bob'


def test_accept_friend_marks_friendship_accepted(client):
    with client.application.app_context():
        alice = create_user(username='alice_accept', email='alice_accept@example.com')
        bob = create_user(username='bob_accept', email='bob_accept@example.com', display_name='Bob')
        friendship = Friendship(user1_id=alice.id, user2_id=bob.id, status='pending')
        db.session.add(friendship)
        db.session.commit()
        friendship_id = friendship.id

    login(client, identifier='bob_accept')
    response = client.post(f'/friends/accept/{friendship_id}', follow_redirects=False)

    assert response.status_code == 302
    with client.application.app_context():
        updated = Friendship.query.get(friendship_id)
        assert updated is not None
        assert updated.status == 'accepted'


def test_remove_friend_deletes_friendship_row(client):
    with client.application.app_context():
        alice = create_user(username='alice_remove', email='alice_remove@example.com')
        bob = create_user(username='bob_remove', email='bob_remove@example.com')
        friendship = Friendship(user1_id=alice.id, user2_id=bob.id, status='accepted')
        db.session.add(friendship)
        db.session.commit()
        friendship_id = friendship.id

    login(client, identifier='alice_remove')
    response = client.post(f'/friends/remove/{friendship_id}', follow_redirects=False)

    assert response.status_code == 302
    with client.application.app_context():
        assert Friendship.query.get(friendship_id) is None


def test_user_search_returns_matching_users(client):
    with client.application.app_context():
        create_user(username='search_alice', email='search_alice@example.com')
        create_user(username='search_bob', email='search_bob@example.com', display_name='Bob Builder')

    login(client, identifier='search_alice')
    response = client.get('/users/search?q=bo')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    usernames = [user['username'] for user in payload['users']]
    assert 'search_bob' in usernames
    assert 'search_alice' not in usernames


def test_results_page_aggregates_scores_and_orders_best_slots(client):
    with client.application.app_context():
        organiser = create_user(username='results_owner', email='results_owner@example.com')
        participant = create_user(username='results_participant', email='results_participant@example.com')
        room = Room(
            title='Results Room',
            description='Heatmap test room',
            date_from=date(2026, 5, 17),
            date_to=date(2026, 5, 17),
            selected_dates='2026-05-17',
            time_start='9:00 AM',
            time_end='10:00 AM',
            duration='30 min',
            organiser_id=organiser.id,
        )
        db.session.add(room)
        db.session.flush()
        db.session.add(RoomParticipant(room_id=room.id, user_id=participant.id, status='awaiting'))
        db.session.add_all([
            Availability(room_id=room.id, user_id=organiser.id, time_slot='2026-05-17 9:00 AM', status='free'),
            Availability(room_id=room.id, user_id=participant.id, time_slot='2026-05-17 9:00 AM', status='maybe'),
            Availability(room_id=room.id, user_id=organiser.id, time_slot='2026-05-17 9:30 AM', status='free'),
            Availability(room_id=room.id, user_id=participant.id, time_slot='2026-05-17 9:30 AM', status='busy'),
        ])
        db.session.commit()
        room_code = room.code

    login(client, identifier='results_owner')
    response = client.get(f'/results/{room_code}')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Best Time' in html
    assert 'Found!' in html

    first_card = re.search(r'id="slot-1".*?data-slot="([^"]+)"', html, re.S)
    second_card = re.search(r'id="slot-2".*?data-slot="([^"]+)"', html, re.S)
    assert first_card is not None
    assert second_card is not None
    assert first_card.group(1) == '2026-05-17 9:00 AM'
    assert second_card.group(1) == '2026-05-17 9:30 AM'


def test_confirm_time_records_confirmed_slot(client):
    with client.application.app_context():
        organiser = create_user(username='confirm_owner', email='confirm_owner@example.com')
        room = Room(
            title='Confirm Room',
            description='Confirm slot test',
            date_from=date(2026, 5, 17),
            date_to=date(2026, 5, 17),
            selected_dates='2026-05-17',
            time_start='9:00 AM',
            time_end='10:00 AM',
            duration='30 min',
            organiser_id=organiser.id,
        )
        db.session.add(room)
        db.session.commit()
        room_code = room.code
        room_id = room.id

    login(client, identifier='confirm_owner')
    response = client.post(
        f'/results/{room_code}/confirm',
        data={'confirmed_slot': '2026-05-17 9:00 AM'},
        follow_redirects=False,
    )

    assert response.status_code == 302
    with client.application.app_context():
        updated_room = Room.query.get(room_id)
        assert updated_room is not None
        assert updated_room.confirmed_slot == '2026-05-17 9:00 AM'


def test_notify_participants_records_suggested_slot(client):
    with client.application.app_context():
        organiser = create_user(username='notify_owner', email='notify_owner@example.com')
        room = Room(
            title='Notify Room',
            description='Notify slot test',
            date_from=date(2026, 5, 17),
            date_to=date(2026, 5, 17),
            selected_dates='2026-05-17',
            time_start='9:00 AM',
            time_end='10:00 AM',
            duration='30 min',
            organiser_id=organiser.id,
        )
        db.session.add(room)
        db.session.commit()
        room_code = room.code
        room_id = room.id

    login(client, identifier='notify_owner')
    response = client.post(
        f'/results/{room_code}/notify',
        data={'notify_slot': '2026-05-17 9:30 AM'},
        follow_redirects=False,
    )

    assert response.status_code == 302
    with client.application.app_context():
        updated_room = Room.query.get(room_id)
        assert updated_room is not None
        assert updated_room.suggested_slot == '2026-05-17 9:30 AM'
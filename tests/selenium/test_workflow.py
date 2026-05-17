import os
import re
import tempfile
import threading
import time
from datetime import date

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Availability, Room, RoomParticipant, User
from config import TestConfig


BASE_URL = 'http://localhost:5000'


def _set_input_value(driver, by, selector, value):
    element = driver.find_element(by, selector)
    driver.execute_script(
        """
        const element = arguments[0];
        const value = arguments[1];
        element.value = value;
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        element,
        value,
    )


def _click_element(driver, by, selector):
    element = driver.find_element(by, selector)
    driver.execute_script('arguments[0].click();', element)


def _seed_selenium_database(app):
    with app.app_context():
        db.create_all()

        organizer = User(
            username='testuser1',
            email='test1@smartmeet.com',
            password_hash=generate_password_hash('Test123!'),
            display_name='Alice',
        )
        friend_target = User(
            username='bob',
            email='bob@example.com',
            password_hash=generate_password_hash('Test123!'),
            display_name='Bob',
        )
        db.session.add_all([organizer, friend_target])
        db.session.flush()

        room = Room(
            title='Seeded Results Room',
            description='Seed data for results workflow',
            date_from=date(2026, 5, 17),
            date_to=date(2026, 5, 17),
            selected_dates='2026-05-17',
            time_start='9:00 AM',
            time_end='10:00 AM',
            duration='30 min',
            organiser_id=organizer.id,
        )
        db.session.add(room)
        db.session.flush()

        db.session.add(RoomParticipant(room_id=room.id, user_id=friend_target.id, status='awaiting'))
        db.session.add_all([
            Availability(room_id=room.id, user_id=organizer.id, time_slot='2026-05-17 9:00 AM', status='free'),
            Availability(room_id=room.id, user_id=friend_target.id, time_slot='2026-05-17 9:00 AM', status='maybe'),
            Availability(room_id=room.id, user_id=organizer.id, time_slot='2026-05-17 9:30 AM', status='free'),
            Availability(room_id=room.id, user_id=friend_target.id, time_slot='2026-05-17 9:30 AM', status='busy'),
        ])
        db.session.commit()

        return {
            'friend_username': friend_target.username,
            'results_room_code': room.code,
            'results_top_slot': '2026-05-17 9:00 AM',
        }


@pytest.fixture(scope='session')
def server():
    fd, db_path = tempfile.mkstemp(suffix='.sqlite')
    os.close(fd)

    class SeleniumTestConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
        SQLALCHEMY_ENGINE_OPTIONS = {
            'connect_args': {'check_same_thread': False},
        }

    app = create_app(SeleniumTestConfig)
    seeded_state = _seed_selenium_database(app)

    thread = threading.Thread(
        target=lambda: app.run(host='127.0.0.1', port=5000, use_reloader=False)
    )
    thread.daemon = True
    thread.start()

    timeout = 10
    start = time.time()
    while True:
        try:
            response = requests.get(BASE_URL)
            if response.status_code == 200:
                break
        except Exception:
            pass
        if time.time() - start > timeout:
            raise RuntimeError('Server did not start in time')
        time.sleep(0.1)

    yield seeded_state


@pytest.fixture()
def driver(server):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--window-size=1440,1200')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    chrome_driver = webdriver.Chrome(options=options)
    chrome_driver.implicitly_wait(0)
    try:
        yield chrome_driver
    finally:
        chrome_driver.quit()


def wait_for(driver, condition, timeout=10):
    return WebDriverWait(driver, timeout).until(condition)


def login(driver, username='testuser1', password='Test123!'):
    driver.get(f'{BASE_URL}/login')
    wait_for(driver, EC.presence_of_element_located((By.NAME, 'identifier')))
    driver.find_element(By.NAME, 'identifier').clear()
    driver.find_element(By.NAME, 'identifier').send_keys(username)
    driver.find_element(By.NAME, 'password').clear()
    driver.find_element(By.NAME, 'password').send_keys(password)
    driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
    wait_for(driver, lambda d: d.current_url != f'{BASE_URL}/login')


def test_landing_page_loads_and_has_correct_title(driver):
    driver.get(BASE_URL)
    wait_for(driver, EC.title_contains('SmartMeet'))
    assert 'SmartMeet' in driver.title


def test_login_with_predefined_test_account_succeeds(driver):
    login(driver)
    assert driver.current_url == f'{BASE_URL}/'


def test_login_with_wrong_password_shows_error_message(driver):
    driver.get(f'{BASE_URL}/login')
    wait_for(driver, EC.presence_of_element_located((By.NAME, 'identifier')))
    driver.find_element(By.NAME, 'identifier').send_keys('testuser1')
    driver.find_element(By.NAME, 'password').send_keys('WrongPass1!')
    driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
    wait_for(driver, EC.presence_of_element_located((By.XPATH, "//*[contains(., 'Invalid username or password.')]")))
    assert 'Invalid username or password.' in driver.page_source


def test_dashboard_is_accessible_after_successful_login(driver):
    login(driver)
    driver.get(f'{BASE_URL}/dashboard')
    wait_for(driver, EC.presence_of_element_located((By.TAG_NAME, 'h2')))
    assert 'Rooms You Created' in driver.page_source


def test_dashboard_redirects_to_login_when_unauthenticated(driver):
    driver.delete_all_cookies()
    driver.get(f'{BASE_URL}/dashboard')
    wait_for(driver, EC.presence_of_element_located((By.NAME, 'identifier')))
    assert '/login' in driver.current_url


def test_logout_works_and_protected_pages_redirect_to_login(driver):
    login(driver)
    wait_for(driver, EC.element_to_be_clickable((By.LINK_TEXT, 'Logout'))).click()
    driver.get(f'{BASE_URL}/dashboard')
    wait_for(driver, EC.presence_of_element_located((By.NAME, 'identifier')))
    assert '/login' in driver.current_url


def test_signup_page_loads_correctly(driver):
    driver.get(f'{BASE_URL}/signup')
    wait_for(driver, EC.presence_of_element_located((By.NAME, 'username')))
    assert 'Sign Up' in driver.title or 'Sign Up' in driver.page_source


def test_signup_with_weak_password_shows_error_message(driver):
    driver.get(f'{BASE_URL}/signup')
    wait_for(driver, EC.presence_of_element_located((By.NAME, 'display_name')))
    driver.find_element(By.NAME, 'display_name').send_keys('Selenium User')
    driver.find_element(By.NAME, 'username').send_keys('seleniumweak')
    driver.find_element(By.NAME, 'email').send_keys('seleniumweak@example.com')
    driver.find_element(By.NAME, 'password').send_keys('weak')
    driver.find_element(By.NAME, 'confirm').send_keys('weak')
    driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
    wait_for(driver, EC.presence_of_element_located((By.XPATH, "//*[contains(., 'Password must be at least 8 characters.')]")))
    assert 'Password must be at least 8 characters.' in driver.page_source


def test_friends_page_loads_after_login(driver):
    login(driver)
    driver.get(f'{BASE_URL}/friends')
    wait_for(driver, EC.url_contains('/friends'))
    assert '/friends' in driver.current_url


def test_settings_page_loads_after_login(driver):
    login(driver)
    driver.get(f'{BASE_URL}/settings')
    wait_for(driver, EC.url_contains('/settings'))
    assert '/settings' in driver.current_url


def test_create_event_and_availability_workflow(driver):
    login(driver)
    driver.get(f'{BASE_URL}/create-event')

    wait_for(driver, EC.presence_of_element_located((By.NAME, 'roomName')))
    _set_input_value(driver, By.NAME, 'roomName', 'Browser Workflow Room')
    _set_input_value(driver, By.NAME, 'roomDesc', 'Created by Selenium')

    _click_element(driver, By.XPATH, "//button[contains(., 'Next: Dates & Time')]")
    wait_for(driver, EC.presence_of_element_located((By.NAME, 'dateFrom')))
    _set_input_value(driver, By.NAME, 'dateFrom', '2026-05-20')
    _set_input_value(driver, By.NAME, 'dateTo', '2026-05-21')
    _set_input_value(driver, By.NAME, 'timeStart', '9:00 AM')
    _set_input_value(driver, By.NAME, 'timeEnd', '5:00 PM')
    _set_input_value(driver, By.NAME, 'duration', '1 hour')

    _click_element(driver, By.XPATH, "//button[contains(., 'Next: Your Info')]")
    wait_for(driver, EC.presence_of_element_located((By.ID, 'createBtn')))
    _click_element(driver, By.ID, 'createBtn')

    wait_for(driver, EC.url_contains('/availability/'))
    assert '/availability/' in driver.current_url

    wait_for(driver, EC.presence_of_element_located((By.CSS_SELECTOR, '#avGrid td.tile')))
    _click_element(driver, By.CSS_SELECTOR, '#avGrid td.tile')
    _click_element(driver, By.CSS_SELECTOR, 'button[type="submit"]')

    wait_for(driver, EC.url_contains('/dashboard'))
    assert '/dashboard' in driver.current_url


def test_friends_interaction_workflow(driver, server):
    login(driver)
    driver.get(f'{BASE_URL}/friends')

    wait_for(driver, EC.presence_of_element_located((By.ID, 'friendSearch')))
    _set_input_value(driver, By.ID, 'friendSearch', server['friend_username'])
    _click_element(driver, By.CSS_SELECTOR, '#addFriendForm button[type="submit"]')

    wait_for(driver, lambda d: 'Sent Requests' in d.page_source or '@bob' in d.page_source)
    assert 'Sent Requests' in driver.page_source
    assert '@bob' in driver.page_source


def test_results_presentation_workflow(driver, server):
    login(driver)
    driver.get(f"{BASE_URL}/results/{server['results_room_code']}")

    wait_for(driver, EC.presence_of_element_located((By.ID, 'rGrid')))
    assert 'Best Time' in driver.page_source
    assert 'Found!' in driver.page_source
    assert 'Availability Heatmap' in driver.page_source

    first_card = re.search(r'id="slot-1".*?data-slot="([^"]+)"', driver.page_source, re.S)
    assert first_card is not None
    assert first_card.group(1) == server['results_top_slot']
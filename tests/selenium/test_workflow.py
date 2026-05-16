import pytest
import threading
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import User
from config import TestConfig


BASE_URL = 'http://localhost:5000'


@pytest.fixture(scope='session')
def server():
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()
        user = User(
            username='testuser1',
            email='test1@smartmeet.com',
            password_hash=generate_password_hash('Test123!'),
            display_name='Alice',
        )
        db.session.add(user)
        db.session.commit()

    thread = threading.Thread(
        target=lambda: app.run(host='127.0.0.1', port=5000, use_reloader=False)
    )
    thread.daemon = True
    thread.start()

    timeout = 10
    start = time.time()
    while True:
        try:
            r = requests.get(BASE_URL)
            if r.status_code == 200:
                break
        except Exception:
            pass
        if time.time() - start > timeout:
            raise RuntimeError('Server did not start in time')
        time.sleep(0.1)

    yield


@pytest.fixture()
def driver(server):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--window-size=1440,1200')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    chrome_driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
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
    wait_for(driver, lambda d: '/dashboard' in d.current_url or d.current_url == f'{BASE_URL}/')


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
    wait_for(driver, EC.presence_of_element_located(
        (By.XPATH, "//*[contains(., 'Invalid username or password.')]")))
    assert 'Invalid username or password.' in driver.page_source


def test_dashboard_is_accessible_after_successful_login(driver):
    login(driver)
    driver.get(f'{BASE_URL}/dashboard')
    wait_for(driver, EC.presence_of_element_located((By.TAG_NAME, 'h2')))
    assert 'welcome back' in driver.page_source.lower()


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
    wait_for(driver, EC.presence_of_element_located(
        (By.XPATH, "//*[contains(., 'Password must be at least 8 characters.')]")))
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